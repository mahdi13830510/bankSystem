
import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch, PropertyMock

from django.test import TestCase, RequestFactory
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.utils import timezone

from apps.fraud.models import FraudReport, FraudDecision
from apps.fraud.services.rules import FraudRules
from apps.fraud.services.ml_scoring import MLScoringService
from apps.fraud.services.risk_engine import RiskEngine
from apps.fraud.services.main_service import FraudService
from apps.fraud.admin import (
    FraudReportAdmin,
    mark_safe_action,
    mark_blocked_action,
    rescore_action,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_report(**kwargs):
    """Create a FraudReport with sane defaults."""
    defaults = dict(
        transaction_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        score=30,
        decision=FraudDecision.SAFE,
        reason={"amount": "500"},
    )
    defaults.update(kwargs)
    return FraudReport.objects.create(**defaults)


def _make_transaction(
    amount=500,
    fee=5,
    txn_type="CARD_TO_CARD",
    hour=14,
    is_weekend=False,
    src_bank_id=1,
    dst_bank_id=1,
    history_count=10,
):
    """Return a mock Transaction object (no DB required)."""
    created_at = MagicMock()
    created_at.hour = hour
    created_at.weekday.return_value = 5 if is_weekend else 1

    src_account = MagicMock()
    src_account.bank_id = src_bank_id
    src_account.transactions.count.return_value = history_count

    dst_account = MagicMock()
    dst_account.bank_id = dst_bank_id

    txn = MagicMock()
    txn.id = uuid.uuid4()
    txn.amount = Decimal(str(amount))
    txn.fee = Decimal(str(fee))
    txn.type = txn_type
    txn.created_at = created_at
    txn.account = src_account
    txn.destination_account = dst_account
    return txn


def _make_user():
    """Return a mock User object."""
    user = MagicMock()
    user.id = uuid.uuid4()
    return user


def _add_messages(request):
    """Attach Django messages framework to a request."""
    setattr(request, "session", {})
    messages = FallbackStorage(request)
    setattr(request, "_messages", messages)
    return request


# ===========================================================================
# 1. FraudRules
# ===========================================================================

class FraudRulesDecideTest(TestCase):

    def test_score_below_50_returns_safe(self):
        self.assertEqual(FraudRules.decide(0), "SAFE")
        self.assertEqual(FraudRules.decide(49), "SAFE")

    def test_score_50_returns_suspicious(self):
        self.assertEqual(FraudRules.decide(50), "SUSPICIOUS")

    def test_score_between_50_and_79_returns_suspicious(self):
        self.assertEqual(FraudRules.decide(79), "SUSPICIOUS")

    def test_score_80_returns_blocked(self):
        self.assertEqual(FraudRules.decide(80), "BLOCKED")

    def test_score_100_returns_blocked(self):
        self.assertEqual(FraudRules.decide(100), "BLOCKED")


# ===========================================================================
# 2. MLScoringService
# ===========================================================================

class MLScoringServiceTest(TestCase):

    def setUp(self):
        # Reset the module-level _artifact cache before each test
        import apps.fraud.services.ml_scoring as ml_mod
        ml_mod._artifact = None

    def test_predict_returns_int(self):
        score = MLScoringService.predict({
            "amount": 500, "hour_of_day": 14, "is_weekend": 0,
            "is_interbank": 0, "history_count": 15,
            "fee_ratio": 0.01, "txn_type_encoded": 1,
        })
        self.assertIsInstance(score, int)

    def test_predict_score_in_range(self):
        score = MLScoringService.predict({
            "amount": 500, "hour_of_day": 14, "is_weekend": 0,
            "is_interbank": 0, "history_count": 15,
            "fee_ratio": 0.01, "txn_type_encoded": 1,
        })
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    @patch("apps.fraud.services.ml_scoring._artifact", None)
    @patch("apps.fraud.services.ml_scoring.os.path.exists", return_value=False)
    def test_fallback_high_amount_returns_60(self, _mock_exists):
        score = MLScoringService.predict({"amount": 9000})
        self.assertEqual(score, 60)

    @patch("apps.fraud.services.ml_scoring._artifact", None)
    @patch("apps.fraud.services.ml_scoring.os.path.exists", return_value=False)
    def test_fallback_low_amount_returns_20(self, _mock_exists):
        score = MLScoringService.predict({"amount": 100})
        self.assertEqual(score, 20)

    @patch("apps.fraud.services.ml_scoring._artifact", None)
    @patch("apps.fraud.services.ml_scoring.os.path.exists", return_value=False)
    def test_missing_features_use_defaults(self, _mock_exists):
        # Should not raise even when dict is empty
        score = MLScoringService.predict({})
        self.assertIn(score, (20, 60))

    def test_train_and_save_produces_valid_artifact(self):
        import numpy as np
        import os

        rng = np.random.default_rng(0)
        X_normal = np.column_stack([
            rng.lognormal(6.5, 1.2, 200).clip(10, 9000),
            rng.choice(np.arange(8, 22), 200).astype(float),
            rng.binomial(1, 0.28, 200).astype(float),
            rng.binomial(1, 0.35, 200).astype(float),
            rng.poisson(12, 200).clip(0, 100).astype(float),
            rng.uniform(0.001, 0.03, 200),
            rng.integers(0, 10, 200).astype(float),
        ])
        X_fraud = np.column_stack([
            rng.lognormal(9.5, 0.8, 10).clip(5000, 200000),
            rng.choice([0, 1, 2, 3, 4, 23], 10).astype(float),
            np.ones(10),
            np.ones(10),
            rng.poisson(1, 10).clip(0, 5).astype(float),
            rng.uniform(0.0001, 0.005, 10),
            rng.integers(0, 10, 10).astype(float),
        ])

        MLScoringService.train_and_save(X_normal, X_fraud)

        from apps.fraud.services.ml_scoring import ARTIFACT_PATH
        self.assertTrue(os.path.exists(ARTIFACT_PATH))

        score = MLScoringService.predict({
            "amount": 500, "hour_of_day": 14, "is_weekend": 0,
            "is_interbank": 0, "history_count": 15,
            "fee_ratio": 0.01, "txn_type_encoded": 1,
        })
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)


# ===========================================================================
# 3. RiskEngine
# ===========================================================================

class RiskEngineTest(TestCase):

    def _score(self, **kwargs):
        txn = _make_transaction(**kwargs)
        return RiskEngine.calculate_score(
            transaction=txn,
            ip="1.2.3.4",
            history_count=kwargs.get("history_count", 10),
        )

    def test_score_within_0_100(self):
        score = self._score()
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    def test_high_amount_raises_score(self):
        low = self._score(amount=100, history_count=20)
        high = self._score(amount=15000, history_count=20)
        self.assertGreater(high, low)

    @patch(
        "apps.fraud.services.risk_engine.MLScoringService.predict",
        return_value=40,
    )
    def test_low_history_raises_score(self, _):
        rich = self._score(history_count=50)
        poor = self._score(history_count=1)

        self.assertGreater(poor, rich)

    def test_odd_hour_raises_score(self):
        day = self._score(hour=12)
        night = self._score(hour=2)
        self.assertGreater(night, day)

    def test_interbank_raises_score(self):
        same = self._score(src_bank_id=1, dst_bank_id=1)
        diff = self._score(src_bank_id=1, dst_bank_id=2)
        self.assertGreater(diff, same)

    def test_score_capped_at_100(self):
        # worst-case combination
        score = self._score(
            amount=50000, fee=1, hour=2,
            is_weekend=True, src_bank_id=1, dst_bank_id=2,
            history_count=0,
        )
        self.assertLessEqual(score, 100)

    def test_txn_type_encoded_correctly(self):
        """RiskEngine should not raise for any known txn type."""
        for txn_type in [
            "CARD_TO_CARD", "INTERNAL_TRANSFER", "IBAN_TRANSFER",
            "CASH_DEPOSIT", "CASH_WITHDRAW",
        ]:
            score = self._score(txn_type=txn_type)
            self.assertGreaterEqual(score, 0)

    def test_missing_destination_account_defaults_to_not_interbank(self):
        txn = _make_transaction()
        del txn.destination_account  # AttributeError path
        score = RiskEngine.calculate_score(
            transaction=txn, ip="1.2.3.4", history_count=10
        )
        self.assertGreaterEqual(score, 0)


# ===========================================================================
# 4. FraudService
# ===========================================================================

class FraudServiceTest(TestCase):

    @patch("apps.notifications.services.NotificationService.send_template")
    @patch("apps.auditlogs.services.AuditLogService.critical")
    @patch("apps.fraud.services.risk_engine.RiskEngine.calculate_score", return_value=30)
    def test_safe_transaction_creates_report(self, _mock_score, mock_audit, mock_notif):
        txn = _make_transaction(amount=200)
        user = _make_user()

        report = FraudService.check_transaction(
            user=user, transaction=txn, ip="1.2.3.4"
        )

        self.assertIsInstance(report, FraudReport)
        self.assertEqual(report.decision, FraudDecision.SAFE)
        self.assertEqual(report.score, 30)
        mock_audit.assert_not_called()
        mock_notif.assert_not_called()

    @patch("apps.notifications.services.NotificationService.send_template")
    @patch("apps.auditlogs.services.AuditLogService.critical")
    @patch("apps.fraud.services.risk_engine.RiskEngine.calculate_score", return_value=60)
    def test_suspicious_transaction_sends_notification(
        self, _mock_score, mock_audit, mock_notif
    ):
        txn = _make_transaction()
        user = _make_user()

        report = FraudService.check_transaction(
            user=user, transaction=txn, ip="1.2.3.4"
        )

        self.assertEqual(report.decision, FraudDecision.SUSPICIOUS)
        mock_audit.assert_called_once()
        mock_notif.assert_called_once()

    @patch("apps.notifications.services.NotificationService.send_template")
    @patch("apps.auditlogs.services.AuditLogService.critical")
    @patch("apps.fraud.services.risk_engine.RiskEngine.calculate_score", return_value=90)
    def test_blocked_transaction_raises_exception(
        self, _mock_score, mock_audit, mock_notif
    ):
        txn = _make_transaction()
        user = _make_user()

        with self.assertRaises(Exception) as ctx:
            FraudService.check_transaction(
                user=user, transaction=txn, ip="1.2.3.4"
            )

        self.assertIn("blocked", str(ctx.exception).lower())

    @patch("apps.notifications.services.NotificationService.send_template")
    @patch("apps.auditlogs.services.AuditLogService.critical")
    @patch("apps.fraud.services.risk_engine.RiskEngine.calculate_score", return_value=90)
    def test_blocked_transaction_persists_report_before_raising(
        self, _mock_score, _mock_audit, _mock_notif
    ):
        txn = _make_transaction()
        user = _make_user()

        with self.assertRaises(Exception):
            FraudService.check_transaction(
                user=user, transaction=txn, ip="1.2.3.4"
            )

        self.assertTrue(
            FraudReport.objects.filter(
                transaction_id=txn.id, decision=FraudDecision.BLOCKED
            ).exists()
        )

    @patch("apps.notifications.services.NotificationService.send_template")
    @patch("apps.auditlogs.services.AuditLogService.critical")
    @patch("apps.fraud.services.risk_engine.RiskEngine.calculate_score", return_value=30)
    def test_report_reason_contains_amount_and_ip(
        self, _mock_score, _mock_audit, _mock_notif
    ):
        txn = _make_transaction(amount=750)
        user = _make_user()

        report = FraudService.check_transaction(
            user=user, transaction=txn, ip="9.9.9.9"
        )

        self.assertIn("amount", report.reason)
        self.assertEqual(report.reason["ip"], "9.9.9.9")

    @patch("apps.notifications.services.NotificationService.send_template")
    @patch("apps.auditlogs.services.AuditLogService.critical")
    @patch("apps.fraud.services.risk_engine.RiskEngine.calculate_score", return_value=30)
    def test_audit_log_not_called_for_safe(
        self, _mock_score, mock_audit, _mock_notif
    ):
        txn = _make_transaction()
        user = _make_user()
        FraudService.check_transaction(user=user, transaction=txn, ip="1.2.3.4")
        mock_audit.assert_not_called()


# ===========================================================================
# 5. FraudReportListView
# ===========================================================================

class FraudReportListViewTest(TestCase):

    def setUp(self):
        _make_report(score=20, decision=FraudDecision.SAFE)
        _make_report(score=60, decision=FraudDecision.SUSPICIOUS)
        _make_report(score=85, decision=FraudDecision.BLOCKED)

    def test_get_returns_200(self):
        response = self.client.get("/fraud/reports/")
        self.assertEqual(response.status_code, 200)

    def test_get_returns_all_reports(self):
        response = self.client.get("/fraud/reports/")
        self.assertEqual(len(response.json()), 3)

    def test_response_contains_required_fields(self):
        response = self.client.get("/fraud/reports/")
        first = response.json()[0]
        for field in ("id", "score", "decision", "transaction_id"):
            self.assertIn(field, first)

    def test_reports_ordered_by_created_at_desc(self):
        response = self.client.get("/fraud/reports/")
        decisions = [r["decision"] for r in response.json()]
        # Most recently created is BLOCKED (last inserted)
        self.assertEqual(decisions[0], "BLOCKED")


# ===========================================================================
# 6. Admin – list-view extra context
# ===========================================================================

class FraudReportAdminChangelistTest(TestCase):

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.admin_user = User.objects.create_superuser(
            phone="09000000000",
            email="admin@test.com",
            password="pass",
            fullname="Admin",
            national_code="0000000001",
        )
        self.client.force_login(self.admin_user)

        _make_report(score=20, decision=FraudDecision.SAFE)
        _make_report(score=60, decision=FraudDecision.SUSPICIOUS)
        _make_report(score=85, decision=FraudDecision.BLOCKED)

    def test_changelist_loads(self):
        response = self.client.get("/admin/fraud/fraudreport/")
        self.assertEqual(response.status_code, 200)

    def test_changelist_context_has_summary_cards(self):
        response = self.client.get("/admin/fraud/fraudreport/")
        cards = response.context["summary_cards"]
        labels = [c["label"] for c in cards]
        self.assertIn("Total Reports", labels)
        self.assertIn("Blocked", labels)

    def test_changelist_total_count_is_correct(self):
        response = self.client.get("/admin/fraud/fraudreport/")
        cards = {c["label"]: c["value"] for c in response.context["summary_cards"]}
        self.assertEqual(cards["Total Reports"], 3)
        self.assertEqual(cards["Blocked"], 1)


# ===========================================================================
# 7. Admin – bulk actions
# ===========================================================================

class AdminActionsTest(TestCase):

    def setUp(self):
        self.site = AdminSite()
        self.model_admin = FraudReportAdmin(FraudReport, self.site)
        self.factory = RequestFactory()

    def _request(self, path="/"):
        req = self.factory.post(path)
        req.user = MagicMock(is_active=True, is_staff=True)
        return _add_messages(req)

    def test_mark_safe_action_updates_decision(self):
        r1 = _make_report(score=85, decision=FraudDecision.BLOCKED)
        r2 = _make_report(score=85, decision=FraudDecision.BLOCKED)

        qs = FraudReport.objects.filter(pk__in=[r1.pk, r2.pk])

        mark_safe_action(self.model_admin, self._request(), qs)

        r1.refresh_from_db()
        r2.refresh_from_db()

        self.assertEqual(r1.decision, FraudDecision.SAFE)
        self.assertEqual(r2.decision, FraudDecision.SAFE)
    def test_mark_blocked_action_updates_decision(self):
        r1 = _make_report(score=10, decision=FraudDecision.SAFE)

        qs = FraudReport.objects.filter(pk=r1.pk)
        mark_blocked_action(self.model_admin, self._request(), qs)

        r1.refresh_from_db()
        self.assertEqual(r1.decision, FraudDecision.BLOCKED)

    @patch("apps.fraud.admin.MLScoringService.predict", return_value=55)
    @patch("apps.fraud.admin.FraudRules.decide", return_value="SUSPICIOUS")
    def test_rescore_action_updates_score_and_decision(
        self, _mock_decide, _mock_predict
    ):
        report = _make_report(
            score=10,
            decision=FraudDecision.SAFE,
            reason={
                "amount": "500", "hour_of_day": "14", "is_weekend": "0",
                "is_interbank": "0", "history": "10", "fee_ratio": "0.01",
                "txn_type_encoded": "1",
            },
        )

        qs = FraudReport.objects.filter(pk=report.pk)
        rescore_action(self.model_admin, self._request(), qs)

        report.refresh_from_db()
        self.assertEqual(report.score, 55)
        self.assertEqual(report.decision, FraudDecision.SUSPICIOUS)

    def test_rescore_action_handles_empty_reason_gracefully(self):
        """rescore should not raise when reason dict is empty."""
        report = _make_report(score=10, decision=FraudDecision.SAFE, reason={})
        qs = FraudReport.objects.filter(pk=report.pk)
        try:
            rescore_action(self.model_admin, self._request(), qs)
        except Exception as exc:
            self.fail(f"rescore_action raised unexpectedly: {exc}")
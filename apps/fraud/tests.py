import uuid

from django.test import TestCase
from unittest.mock import MagicMock, patch

from rest_framework.test import APITestCase

from apps.banks.models import BankStatus
from apps.fraud.services.main_service import FraudService
from apps.fraud.services.risk_engine import RiskEngine
from apps.fraud.services.rules import FraudRules
from apps.fraud.models import FraudReport, FraudDecision


class FraudBaseTest(TestCase):

    def make_bank(self, bank_id=1, status=None):
        bank = MagicMock()
        bank.id = bank_id
        bank.status = status
        return bank

    def make_transaction(self, amount, source_bank, dest_bank):
        tx = MagicMock()
        tx.id = uuid.uuid4()
        tx.amount = amount
        tx.account.bank = source_bank
        tx.destination_account.bank = dest_bank
        tx.account.transactions.count.return_value = 0
        return tx

    def make_user(self):
        user = MagicMock()
        user.id = uuid.uuid4()
        return user


class RiskEngineTest(FraudBaseTest):

    def test_full_risk_score(self):
        source = self.make_bank(1)
        dest = self.make_bank(2)

        tx = self.make_transaction(12000, source, dest)

        score = RiskEngine.calculate_score(
            transaction=tx,
            ip="127.0.0.1",
            history_count=6
        )

        # 30 + 20 + 20 + 10 = 80
        self.assertEqual(score, 80)

    def test_suspended_bank(self):
        source = self.make_bank(1)
        dest = self.make_bank(2)
        dest.status = "SUSPENDED"

        tx = self.make_transaction(1000, source, dest)

        score = RiskEngine.calculate_score(
            transaction=tx,
            ip="127.0.0.1",
            history_count=0
        )

        self.assertEqual(score, 60)


class FraudRulesTest(TestCase):

    def test_safe(self):
        self.assertEqual(FraudRules.decide(10), "SAFE")

    def test_suspicious(self):
        self.assertEqual(FraudRules.decide(60), "SUSPICIOUS")

    def test_blocked(self):
        self.assertEqual(FraudRules.decide(85), "BLOCKED")


class FraudServiceTest(FraudBaseTest):

    @patch("apps.fraud.services.main_service.AuditLogService.critical")
    @patch("apps.fraud.services.main_service.NotificationService.send_template")
    def test_safe_transaction_creates_report(self, mock_notify, mock_audit):
        user = self.make_user()
        source = self.make_bank(1)
        dest = self.make_bank(1)

        tx = self.make_transaction(1000, source, dest)

        report = FraudService.check_transaction(
            user=user,
            transaction=tx,
            ip="127.0.0.1"
        )

        self.assertEqual(report.decision, FraudDecision.SAFE)
        self.assertEqual(FraudReport.objects.count(), 1)

        mock_notify.assert_called_once()
        mock_audit.assert_called_once()

    @patch("apps.fraud.services.main_service.AuditLogService.critical")
    @patch("apps.fraud.services.main_service.NotificationService.send_template")
    def test_suspicious_transaction(self, mock_notify, mock_audit):
        user = self.make_user()
        source = self.make_bank(1)
        dest = self.make_bank(2)

        tx = self.make_transaction(15000, source, dest)

        report = FraudService.check_transaction(
            user=user,
            transaction=tx,
            ip="127.0.0.1"
        )

        self.assertEqual(report.decision, FraudDecision.SUSPICIOUS)

    @patch("apps.fraud.services.main_service.AuditLogService.critical")
    @patch("apps.fraud.services.main_service.NotificationService.send_template")
    def test_blocked_transaction_raises_exception(self, mock_notify, mock_audit):
        user = self.make_user()
        source = self.make_bank(1)
        dest = self.make_bank(2)
        dest.status = BankStatus.SUSPENDED

        tx = self.make_transaction(20000, source, dest)

        with self.assertRaises(Exception):
            FraudService.check_transaction(
                user=user,
                transaction=tx,
                ip="127.0.0.1"
            )

        mock_notify.assert_not_called()


class FraudReportListViewTest(APITestCase):

    def test_list_reports(self):
        FraudReport.objects.create(
            transaction_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            score=50,
            decision="SUSPICIOUS",
            reason={}
        )

        response = self.client.get("/fraud/reports/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

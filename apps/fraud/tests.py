from django.test import TestCase
from apps.fraud.services.risk_engine import RiskEngine
from apps.fraud.services.rules import FraudRules
from unittest.mock import MagicMock
from apps.fraud.services.main_service import FraudService
from unittest.mock import patch


class RiskEngineTests(TestCase):

    def test_high_amount_increases_score(self):
        score = RiskEngine.calculate_score(
            user=None,
            amount=12000,
            ip="8.8.8.8",
            history_count=0
        )
        self.assertGreaterEqual(score, 50)

    def test_low_amount_returns_low_score(self):
        score = RiskEngine.calculate_score(
            user=None,
            amount=100,
            ip="8.8.8.8",
            history_count=0
        )
        self.assertLess(score, 30)


class FraudRulesTests(TestCase):

    def test_blocked_rule(self):
        self.assertEqual(FraudRules.decide(90), "BLOCKED")

    def test_suspicious_rule(self):
        self.assertEqual(FraudRules.decide(70), "SUSPICIOUS")

    def test_safe_rule(self):
        self.assertEqual(FraudRules.decide(20), "SAFE")


class FraudServiceTests(TestCase):

    def setUp(self):
        self.user = MagicMock()
        self.user.id = "user-1"

        self.transaction = MagicMock()
        self.transaction.id = "txn-1"
        self.transaction.amount = 5000
        self.transaction.account.transactions.count.return_value = 1

    def test_fraud_service_returns_report(self):
        report = FraudService.check_transaction(
            user=self.user,
            transaction=self.transaction,
            ip="1.1.1.1"
        )

        self.assertIsNotNone(report)
        self.assertTrue(hasattr(report, "score"))


class FraudBlockTests(TestCase):

    def test_blocked_transaction_raises_exception(self):
        user = MagicMock()
        user.id = "u1"

        txn = MagicMock()
        txn.id = "t1"
        txn.amount = 20000
        txn.account.transactions.count.return_value = 10

        with self.assertRaises(Exception):
            FraudService.check_transaction(
                user=user,
                transaction=txn,
                ip="1.1.1.1"
            )


class FraudIntegrationTests(TestCase):

    @patch("apps.fraud.services.fraud_service.AuditLogService.log")
    def test_audit_log_called(self, mock_log):

        user = type("U", (), {"id": "1"})()
        txn = type("T", (), {
            "id": "1",
            "amount": 1000,
            "account": type("A", (), {"transactions": type("X", (), {"count": lambda: 1})()})()
        })()

        FraudService.check_transaction(
            user=user,
            transaction=txn,
            ip="1.1.1.1"
        )

        self.assertTrue(mock_log.called)

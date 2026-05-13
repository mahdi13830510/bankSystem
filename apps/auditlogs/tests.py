from django.test import TestCase
from apps.auditlogs.services import AuditLogService
from apps.auditlogs.models import AuditLog
from unittest.mock import patch
from apps.fraud.services.main_service import FraudService


class AuditLogTests(TestCase):

    def test_create_audit_log(self):
        log = AuditLogService.log(
            user=None,
            action="LOGIN",
            entity_type="AUTH",
            entity_id="123"
        )

        self.assertIsNotNone(log.id)


class AuditLogModelTests(TestCase):

    def test_metadata_saved(self):
        log = AuditLog.objects.create(
            action="LOGIN",
            entity_type="AUTH",
            entity_id="1",
            metadata={"ip": "127.0.0.1"}
        )

        self.assertEqual(log.metadata["ip"], "127.0.0.1")


class AuditIntegrationTests(TestCase):

    @patch("apps.auditlog.services.AuditLogService.log")
    def test_fraud_calls_auditlog(self, mock_log):

        user = type("U", (), {"id": "1"})()
        txn = type("T", (), {
            "id": "1",
            "amount": 1000,
            "account": type("A", (), {"transactions": type("X", (), {"count": lambda: 0})()})()
        })()

        FraudService.check_transaction(
            user=user,
            transaction=txn,
            ip="1.1.1.1"
        )

        mock_log.assert_called()
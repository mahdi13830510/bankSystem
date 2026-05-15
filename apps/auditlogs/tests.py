from django.test import TestCase
from apps.users.models import User
from .models import AuditLog
from .services import AuditLogService


class AuditLogTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            phone="09120000000",
            password="1234",
            email="testemail@gmail.com"
        )

    def test_create_log(self):
        AuditLogService.log(
            actor=self.user,
            action="LOGIN_SUCCESS"
        )

        self.assertEqual(
            AuditLog.objects.count(),
            1
        )

    def test_warning_log(self):
        AuditLogService.warning(
            actor=self.user,
            action="FAILED_LOGIN"
        )

        log = AuditLog.objects.first()

        self.assertEqual(log.severity, "WARNING")

from decimal import Decimal
from django.test import TestCase
from unittest.mock import patch

from apps.accounts.models import Account
from apps.transactions.services import TransactionService
from apps.users.models import User
from rest_framework.test import APITestCase
from django.urls import reverse


class TransactionServiceTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            phone="09120000000",
            password="123456"
        )

        self.source = Account.objects.create(
            customer=self.user,
            balance=Decimal("10000")
        )

        self.destination = Account.objects.create(
            customer=self.user,
            balance=Decimal("5000")
        )

    @patch("apps.transactions.services.FraudService.check_transaction")
    @patch("apps.transactions.services.AuditLogService.log")
    @patch("apps.transactions.services.NotificationService.send_sms")
    def test_card_transfer_success(self, mock_sms, mock_audit, mock_fraud):

        txn = TransactionService.card_transfer(
            actor=self.user,
            source=self.source,
            destination=self.destination,
            amount=Decimal("1000"),
            ip="127.0.0.1"
        )

        self.source.refresh_from_db()
        self.destination.refresh_from_db()

        self.assertEqual(txn.amount, Decimal("1000"))
        self.assertEqual(self.source.balance, Decimal("8999"))  # fee included
        self.assertEqual(self.destination.balance, Decimal("6000"))

        mock_fraud.assert_called_once()
        mock_audit.assert_called_once()
        mock_sms.assert_called_once()

    def test_insufficient_balance(self):

        with self.assertRaises(Exception):
            TransactionService.card_transfer(
                actor=self.user,
                source=self.source,
                destination=self.destination,
                amount=Decimal("999999"),
                ip="127.0.0.1"
            )


class TransactionViewTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            phone="09120000000",
            password="123456"
        )

        self.client.force_authenticate(user=self.user)

        self.source = Account.objects.create(
            customer=self.user,
            balance=Decimal("10000")
        )

        self.destination = Account.objects.create(
            customer=self.user,
            balance=Decimal("2000")
        )

    def test_card_transfer_api(self):

        url = reverse("card-transfer")

        response = self.client.post(url, {
            "source_account_id": str(self.source.id),
            "destination_account_id": str(self.destination.id),
            "amount": "1000"
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn("reference_number", response.data)


class TransactionIntegrationTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            phone="09120000000",
            password="123456"
        )

        self.acc1 = Account.objects.create(
            customer=self.user,
            balance=Decimal("5000")
        )

        self.acc2 = Account.objects.create(
            customer=self.user,
            balance=Decimal("1000")
        )

    def test_full_transfer_flow(self):

        txn = TransactionService.card_transfer(
            actor=self.user,
            source=self.acc1,
            destination=self.acc2,
            amount=Decimal("1000"),
            ip="127.0.0.1"
        )

        self.assertIsNotNone(txn.id)
        self.assertEqual(txn.status, "SUCCESS")
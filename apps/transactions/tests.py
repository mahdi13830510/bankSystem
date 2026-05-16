from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import User
from apps.banks.models import Bank
from apps.accounts.models import Account
from apps.transactions.models import (
    Transaction,
    TransactionType,
    TransactionStatus,
)
from apps.transactions.services import TransactionService


class TransactionServiceTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            phone="09120000001",
            password="123456",
            email="test@gmail.com"
        )

        self.bank = Bank.objects.create(
            name="Test Bank",
            code="TB",
            transfer_fee=Decimal("5.00")
        )

        self.source = Account.objects.create(
            customer=self.user,
            bank=self.bank,
            account_number="111111111111",
            iban="IR11111111111111111111",
            balance=Decimal("1000.00"),
            status="ACTIVE"
        )

        self.destination = Account.objects.create(
            customer=self.user,
            bank=self.bank,
            account_number="222222222222",
            iban="IR22222222222222222222",
            balance=Decimal("500.00"),
            status="ACTIVE"
        )

    @patch("apps.transactions.services.NotificationService.send_template")
    @patch("apps.transactions.services.AuditLogService.info")
    @patch("apps.transactions.services.LimitService.validate_daily_transfer_limit")
    @patch("apps.transactions.services.FraudService.check_transaction")
    def test_card_transfer_success(
        self,
        fraud_mock,
        limit_mock,
        audit_mock,
        template_mock,

    ):
        fraud_mock.return_value = SimpleNamespace(score=25)

        txn = TransactionService.card_transfer(
            actor=self.user,
            source=self.source,
            destination=self.destination,
            amount=Decimal("100"),
            ip="127.0.0.1",
            description="test"
        )

        self.source.refresh_from_db()
        self.destination.refresh_from_db()
        txn.refresh_from_db()

        self.assertEqual(txn.status, TransactionStatus.SUCCESS)
        self.assertEqual(self.source.balance, Decimal("895.00"))
        self.assertEqual(self.destination.balance, Decimal("600.00"))

    @patch("apps.transactions.services.LimitService.validate_daily_transfer_limit")
    def test_card_transfer_insufficient_balance(self, _):
        with self.assertRaises(Exception):
            TransactionService.card_transfer(
                actor=self.user,
                source=self.source,
                destination=self.destination,
                amount=Decimal("99999"),
                ip="127.0.0.1"
            )

    @patch("apps.transactions.services.FraudService.check_transaction")
    @patch("apps.transactions.services.AuditLogService.info")
    def test_iban_transfer_success(self, audit_mock, fraud_mock):
        fraud_mock.return_value = True

        txn = TransactionService.iban_transfer(
            actor=self.user,
            source=self.source,
            destination=self.destination,
            amount=Decimal("50"),
            ip="127.0.0.1"
        )

        self.source.refresh_from_db()
        self.destination.refresh_from_db()

        self.assertEqual(txn.type, TransactionType.IBAN_TRANSFER)
        self.assertEqual(self.source.balance, Decimal("948.00"))
        self.assertEqual(self.destination.balance, Decimal("550.00"))

    def test_loan_disbursement(self):
        loan = SimpleNamespace(id=1)

        txn = TransactionService.loan_disbursement(
            self.source,
            Decimal("200"),
            loan
        )

        self.assertEqual(txn.type, TransactionType.LOAN_DISBURSEMENT)

    def test_installment_payment(self):
        installment = SimpleNamespace(id=5)

        txn = TransactionService.installment_payment(
            self.source,
            Decimal("80"),
            installment
        )

        self.assertEqual(txn.type, TransactionType.INSTALLMENT_PAYMENT)

    def test_late_fee(self):
        loan = SimpleNamespace(id=2)

        txn = TransactionService.late_fee(
            self.source,
            Decimal("10"),
            loan
        )

        self.assertEqual(txn.type, TransactionType.LATE_FEE)


class TransactionViewTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            phone="09120000002",
            password="123456",
            email="test2@gmail.com"
        )

        self.client.force_authenticate(self.user)

        self.bank = Bank.objects.create(
            name="Bank",
            code="BK",
            transfer_fee=Decimal("5.00")
        )

        self.source = Account.objects.create(
            customer=self.user,
            bank=self.bank,
            account_number="333333333333",
            iban="IR33333333333333333333",
            balance=Decimal("1000"),
            status="ACTIVE"
        )

        self.destination = Account.objects.create(
            customer=self.user,
            bank=self.bank,
            account_number="444444444444",
            iban="IR44444444444444444444",
            balance=Decimal("500"),
            status="ACTIVE"
        )

    @patch("apps.transactions.views.TransactionService.card_transfer")
    def test_card_transfer_view(self, service_mock):

        txn = Transaction.objects.create(
            account=self.source,
            amount=Decimal("100"),
            fee=Decimal("5"),
            type=TransactionType.CARD_TO_CARD,
            status=TransactionStatus.SUCCESS,
            reference_number="REF123"
        )

        service_mock.return_value = txn

        response = self.client.post(
            "/api/transactions/card-transfer/",
            {
                "source_account_id": self.source.id,
                "destination_account_id": self.destination.id,
                "amount": "100.00"
            },
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("apps.transactions.views.TransactionService.iban_transfer")
    def test_iban_transfer_view(self, service_mock):

        txn = Transaction.objects.create(
            account=self.source,
            amount=Decimal("50"),
            fee=Decimal("2"),
            type=TransactionType.IBAN_TRANSFER,
            status=TransactionStatus.SUCCESS,
            reference_number="REF456"
        )

        service_mock.return_value = txn

        response = self.client.post(
            "/api/transactions/iban-transfer/",
            {
                "source_account_id": self.source.id,
                "destination_iban": self.destination.iban,
                "amount": "50.00"
            },
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_statement_view(self):

        Transaction.objects.create(
            account=self.source,
            amount=Decimal("10"),
            fee=0,
            type=TransactionType.CARD_TO_CARD,
            status=TransactionStatus.SUCCESS,
            reference_number="REF999"
        )

        response = self.client.get(
            f"/api/transactions/statement/{self.source.id}/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
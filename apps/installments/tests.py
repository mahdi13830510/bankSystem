from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from dateutil.relativedelta import relativedelta

from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from apps.loans.models import Loan, LoanRequest, LoanType
from apps.installments.models import Installment, InstallmentStatus
from apps.installments.services import InstallmentService

from apps.installments.cron import check_overdue_installments
from apps.installments.cron import send_due_reminders

User = get_user_model()


class InstallmentBaseTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(email="testuser@gmail.com",
                                             phone="09145670989",
                                             password="password123")

        self.loan_request = LoanRequest.objects.create(
            customer=self.user,
            amount=Decimal("12000.00"),
            duration_months=12,
            loan_type=LoanType.PERSONAL,
            monthly_income=Decimal("5000.00")
        )

        self.loan = Loan.objects.create(
            customer=self.user,
            loan_request=self.loan_request,
            principal_amount=Decimal("12000.00"),
            interest_rate=Decimal("10.00"),
            total_payable=Decimal("13200.00"),
            monthly_installment=Decimal("1100.00"),
            duration_months=12
        )


class TestInstallmentService(InstallmentBaseTestCase):

    def test_generate_schedule(self):
        InstallmentService.generate_schedule(self.loan)

        installments = Installment.objects.filter(loan=self.loan)

        self.assertEqual(installments.count(), self.loan.duration_months)
        self.assertEqual(installments.first().amount, self.loan.monthly_installment)
        last_due_date = timezone.now().date() + relativedelta(months=12)
        self.assertEqual(installments.last().due_date, last_due_date)

    @patch("apps.installments.services.AccountService.get_primary_account")
    @patch("apps.installments.services.TransactionService.installment_payment")
    @patch("apps.installments.services.AuditLogService.log")
    def test_pay_installment_success(self, mock_log, mock_trans, mock_account):
        installment = Installment.objects.create(
            loan=self.loan,
            number=1,
            due_date=timezone.now().date(),
            amount=Decimal("1100.00")
        )

        mock_acc_obj = MagicMock()
        mock_acc_obj.balance = Decimal("2000.00")
        mock_account.return_value = mock_acc_obj

        InstallmentService.pay_installment(self.user, installment)

        self.assertEqual(mock_acc_obj.balance, Decimal("900.00"))  # 2000 - 1100
        installment.refresh_from_db()
        self.assertEqual(installment.status, InstallmentStatus.PAID)
        self.assertEqual(installment.paid_amount, Decimal("1100.00"))
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.paid_amount, Decimal("1100.00"))
        mock_trans.assert_called_once()
        mock_log.assert_called_once()

    @patch("apps.installments.services.AccountService.get_primary_account")
    def test_pay_installment_insufficient_balance(self, mock_account):
        installment = Installment.objects.create(
            loan=self.loan, number=1, due_date=timezone.now().date(), amount=Decimal("1000.00")
        )

        mock_acc_obj = MagicMock()
        mock_acc_obj.balance = Decimal("500.00")
        mock_account.return_value = mock_acc_obj

        with self.assertRaises(Exception) as context:
            InstallmentService.pay_installment(self.user, installment)

        self.assertEqual(str(context.exception), "Insufficient balance")

    def test_apply_penalty(self):
        installment = Installment.objects.create(
            loan=self.loan, number=1, due_date=timezone.now().date(), amount=Decimal("1000.00")
        )

        InstallmentService.apply_penalty(installment)

        self.assertEqual(installment.status, InstallmentStatus.OVERDUE)
        self.assertEqual(installment.penalty_amount, Decimal("50.00"))

    def test_remaining_debt(self):
        self.loan.paid_amount = Decimal("5000.00")
        self.loan.save()

        debt = InstallmentService.remaining_debt(self.loan)
        expected = self.loan.total_payable - Decimal("5000.00")
        self.assertEqual(debt, expected)


class TestInstallmentAPIs(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(email="testuser@gmail.com",phone="09145670989",
                                             password="password")
        self.client.force_authenticate(user=self.user)

        lr = LoanRequest.objects.create(customer=self.user, amount=1000, duration_months=1,
                                        loan_type=LoanType.CAR,
                                        monthly_income=5000)
        self.loan = Loan.objects.create(
            customer=self.user, loan_request=lr, principal_amount=1000,
            interest_rate=5, total_payable=1050, monthly_installment=1050, duration_months=1
        )
        self.installment = Installment.objects.create(
            loan=self.loan, number=1, due_date=timezone.now().date(), amount=1050
        )

    def test_my_installments_list(self):
        url = "/installments/my/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], str(self.installment.id))

    @patch("apps.installments.services.InstallmentService.pay_installment")
    def test_pay_installment_api(self, mock_pay):
        url = f"/installments/{self.installment.id}/pay/"
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["detail"], "paid")
        mock_pay.assert_called_once()

    def test_remaining_debt_api(self):
        url = f"/installments/loan/{self.loan.id}/remaining/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("remaining_debt", response.data)
        self.assertEqual(Decimal(str(response.data["remaining_debt"])), Decimal("1050.00"))


class TestInstallmentTasks(InstallmentBaseTestCase):

    @patch("apps.installments.services.InstallmentService.apply_penalty")
    def test_check_overdue_task(self, mock_penalty):

        yesterday = timezone.now().date() - timezone.timedelta(days=1)
        Installment.objects.create(
            loan=self.loan, number=1, due_date=yesterday, amount=1000,
            status=InstallmentStatus.PENDING
        )

        check_overdue_installments()
        mock_penalty.assert_called_once()

    @patch("apps.notifications.services.NotificationService.send_template")
    def test_send_reminders_task(self, mock_notif):

        tomorrow = timezone.now().date() + timezone.timedelta(days=1)
        Installment.objects.create(
            loan=self.loan, number=1, due_date=tomorrow, amount=1000,
            status=InstallmentStatus.PENDING
        )

        send_due_reminders()
        mock_notif.assert_called_once()
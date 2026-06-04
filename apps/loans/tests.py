from unittest.mock import patch, MagicMock
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.loans.calculators import LoanCalculator
from apps.loans.models import LoanRequest, Loan, LoanRequestStatus
from apps.loans.services import LoanService

from rest_framework.test import APITestCase
from rest_framework import status


User = get_user_model()


class LoanCalculatorTest(TestCase):
    def test_calculate_total(self):
        amount = Decimal("1000.00")
        total = LoanCalculator.calculate_total(amount, 12, 10)
        self.assertEqual(total, Decimal("1100.00"))

    def test_monthly_installment(self):
        total = Decimal("1200.00")
        months = 12
        installment = LoanCalculator.monthly_installment(total, months)
        self.assertEqual(installment, Decimal("100.00"))


class LoanServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="testuser@gmail.com"
                                             ,phone="09145670987",national_code="1111111111"
                                             , password="password")
        self.admin = User.objects.create_superuser(email="testser@gmail.com",
                                                   phone="09135670987", password="password")

    @patch('apps.auditlogs.services.AuditLogService.log')
    def test_create_request(self, mock_log):
        data = {
            "amount": Decimal("5000.00"),
            "duration_months": 12,
            "loan_type": "PERSONAL",
            "monthly_income": Decimal("2000.00"),
            "existing_debt": Decimal("500.00")
        }
        req = LoanService.create_request(self.user, data)

        self.assertEqual(LoanRequest.objects.count(), 1)
        self.assertEqual(req.customer, self.user)
        mock_log.assert_called_once()

    def test_evaluate_request_high_risk(self):
        req = LoanRequest.objects.create(
            customer=self.user,
            amount=Decimal("100000.00"),
            duration_months=12,
            monthly_income=Decimal("5000.00"),
            existing_debt=Decimal("3000.00"),
            loan_type="PERSONAL"
        )
        score = LoanService.evaluate_request(req)
        self.assertEqual(score, 70)
        self.assertEqual(req.status, LoanRequestStatus.UNDER_REVIEW)

    @patch('apps.accounts.services.AccountService.get_primary_account')
    @patch('apps.notifications.services.NotificationService.send_template')
    @patch('apps.installments.services.InstallmentService.generate_schedule')
    @patch('apps.transactions.services.TransactionService.loan_disbursement')
    @patch('apps.auditlogs.services.AuditLogService.log')
    def test_approve_request(self, mock_log, mock_trans, mock_inst, mock_notif, mock_acc_service):
        req = LoanRequest.objects.create(
            customer=self.user,
            amount=Decimal("1000.00"),
            duration_months=10,
            monthly_income=Decimal("5000.00"),
            loan_type="PERSONAL"
        )

        mock_account = MagicMock()
        mock_account.balance = Decimal("0.00")
        mock_acc_service.return_value = mock_account

        loan = LoanService.approve_request(self.admin, req)

        self.assertEqual(Loan.objects.count(), 1)
        self.assertEqual(req.status, LoanRequestStatus.APPROVED)

        self.assertEqual(mock_account.balance, Decimal("1000.00"))
        mock_account.save.assert_called()

        mock_inst.assert_called_once()
        mock_notif.assert_called_once()
        mock_trans.assert_called_once()


class LoanAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="tesuser@gmail.com",phone="09155670987",
                                             national_code="11111111111",
                                             password="password123")
        self.admin = User.objects.create_superuser(email="testuser@gmail.com",phone="09145670987",
                                                   password="password123")
        self.client.login(email="tesuser@gmail.com", password="password123")

    def test_create_loan_request_api(self):
        self.client.force_authenticate(user=self.user)

        url = "/loans/request/"
        data = {
            "amount": "10000.00",
            "duration_months": 24,
            "loan_type": "CAR",
            "monthly_income": "5000.00",
            "existing_debt": "1000.00"
        }
        response = self.client.post(url, data,format="json")
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED)
        self.assertTrue("id" in response.data)
        self.assertEqual(LoanRequest.objects.count(), 1)

    def test_my_loan_requests_list(self):
        self.client.force_authenticate(user=self.user)
        LoanRequest.objects.create(
            customer=self.user, amount=5000, duration_months=12,
            monthly_income=2000, loan_type="PERSONAL"
        )
        url = "/loans/my-requests/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_admin_approve_permission(self):
        req = LoanRequest.objects.create(
            customer=self.user, amount=5000, duration_months=12,
            monthly_income=2000, loan_type="PERSONAL"
        )

        url = f"/loans/admin/requests/{req.id}/approve/"

        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.force_authenticate(user=self.admin)

        from decimal import Decimal

        with patch('apps.loans.services.LoanService.approve_request') as mock_approve:
            loan = Loan.objects.create(
                customer=self.user,
                loan_request=req,
                principal_amount=Decimal("5000.00"),
                interest_rate=Decimal("10.00"),
                total_payable=Decimal("5500.00"),
                monthly_installment=Decimal("458.33"),
                duration_months=12,
            )

            mock_approve.return_value = loan

            response = self.client.post(url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_reject_loan_api(self):
        req = LoanRequest.objects.create(
            customer=self.user, amount=5000, duration_months=12,
            monthly_income=2000, loan_type="PERSONAL"
        )
        self.client.force_authenticate(user=self.admin)
        url = f"/loans/admin/requests/{req.id}/reject/"

        with patch('apps.loans.services.LoanService.reject_request'):
            response = self.client.post(url, {"reason": "Low income balance"})
            self.assertEqual(response.status_code, status.HTTP_200_OK)
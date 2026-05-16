from decimal import Decimal
from django.db import transaction

from .models import LoanRequest, Loan, LoanRequestStatus
from .calculators import LoanCalculator

from apps.auditlogs.services import AuditLogService
from apps.notifications.services import NotificationService
from apps.installments.services import InstallmentService
from apps.accounts.services import AccountService
from apps.transactions.services import TransactionService
from apps.notifications.templates import NotificationTemplates


class LoanService:

    @staticmethod
    def create_request(user, data):

        req = LoanRequest.objects.create(
            customer=user,
            **data
        )

        AuditLogService.log(
            actor=user,
            action="LOAN_REQUEST_CREATED",
            metadata={"loan_request_id": str(req.id)}
        )

        return req

    @staticmethod
    def evaluate_request(req):

        score = 0

        debt_ratio = req.existing_debt / req.monthly_income

        if debt_ratio > Decimal("0.5"):
            score += 40

        if req.amount > req.monthly_income * 12:
            score += 30

        req.risk_score = score
        req.status = LoanRequestStatus.UNDER_REVIEW
        req.save()

        return score

    @staticmethod
    @transaction.atomic
    def approve_request(manager, req):

        total = LoanCalculator.calculate_total(
            req.amount,
            annual_rate=18,
            months=req.duration_months
        )

        monthly = LoanCalculator.monthly_installment(
            total,
            req.duration_months
        )

        loan = Loan.objects.create(
            customer=req.customer,
            loan_request=req,
            principal_amount=req.amount,
            interest_rate=18,
            total_payable=total,
            monthly_installment=monthly,
            duration_months=req.duration_months
        )
        account = AccountService.get_primary_account(req.customer)

        account.balance += req.amount
        account.save(update_fields=["balance"])

        TransactionService.loan_disbursement(
            account=account,
            amount=req.amount,
            loan=loan
        )

        req.status = LoanRequestStatus.APPROVED
        req.save()

        # create installments
        InstallmentService.generate_schedule(loan)

        NotificationService.send_template(
            req.customer,
            NotificationTemplates.LOAN_APPROVED
        )

        AuditLogService.log(
            actor=manager,
            action="LOAN_APPROVED",
            metadata={"loan_id": str(loan.id)}
        )

        return loan

    @staticmethod
    def reject_request(manager, req, reason):

        req.status = LoanRequestStatus.REJECTED
        req.manager_note = reason
        req.save()

        NotificationService.send(
            user=req.customer,
            title="Loan Rejected",
            message=reason
        )

        AuditLogService.log(
            actor=manager,
            action="LOAN_REJECTED",
            metadata={"loan_request_id": str(req.id)}
        )
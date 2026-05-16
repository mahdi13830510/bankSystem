from decimal import Decimal

from django.utils import timezone
from django.db import transaction

from dateutil.relativedelta import relativedelta

from .models import Installment, InstallmentStatus

from apps.accounts.services import AccountService
from apps.transactions.services import TransactionService
from apps.auditlogs.services import AuditLogService


class InstallmentService:

    @staticmethod
    def generate_schedule(loan):

        due = timezone.now().date() + relativedelta(months=1)

        for i in range(1, loan.duration_months + 1):
            Installment.objects.create(
                loan=loan,
                number=i,
                due_date=due,
                amount=loan.monthly_installment
            )

            due += relativedelta(months=1)

    @staticmethod
    @transaction.atomic
    def pay_installment(user, installment):

        account = AccountService.get_primary_account(user)

        total_due = installment.amount + installment.penalty_amount

        if account.balance < total_due:
            raise Exception("Insufficient balance")

        account.balance -= total_due
        account.save(update_fields=["balance"])

        installment.paid_amount = total_due
        installment.status = InstallmentStatus.PAID
        installment.paid_at = timezone.now()
        installment.save()

        loan = installment.loan
        loan.paid_amount += total_due
        loan.save(update_fields=["paid_amount"])

        TransactionService.installment_payment(
            account=account,
            amount=total_due,
            installment=installment
        )

        AuditLogService.log(
            actor=user,
            action="INSTALLMENT_PAID",
            metadata={"installment_id": str(installment.id)}
        )

        return installment

    @staticmethod
    def apply_penalty(installment):

        if installment.status == InstallmentStatus.PAID:
            return

        installment.status = InstallmentStatus.OVERDUE
        installment.penalty_amount += Decimal("50.00")
        installment.save()

    @staticmethod
    def remaining_debt(loan):

        total = loan.total_payable
        paid = loan.paid_amount

        return total - paid
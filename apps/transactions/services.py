import uuid
from decimal import Decimal
from django.db import transaction as db_transaction

from apps.accounts.models import Account
from apps.auditlogs.services import AuditLogService
from apps.notifications.services import NotificationService
from apps.fraud.services import main_service
from apps.core.services import LimitService

from .models import (
    Transaction,
    TransactionType,
    TransactionStatus
)
from ..notifications.templates import NotificationTemplates


class TransactionService:

    @staticmethod
    def generate_reference():
        return str(uuid.uuid4()).replace("-", "")[:24]

    @staticmethod
    @db_transaction.atomic
    def card_transfer(*, actor, source, destination, amount, ip, description=""):

        main_service.check_transaction(
            actor=actor,
            source=source,
            destination=destination,
            amount=amount,
            ip=ip
        )

        LimitService.validate_daily_transfer_limit(
            account=source,
            amount=amount
        )

        fee = destination.bank.transfer_fee
        total = amount + fee

        if source.balance < total:
            raise Exception("Insufficient balance")

        source.balance -= total
        destination.balance += amount

        source.save(update_fields=["balance"])
        destination.save(update_fields=["balance"])

        txn = Transaction.objects.create(
            account=source,
            amount=amount,
            fee=fee,
            type=TransactionType.CARD_TO_CARD,
            status=TransactionStatus.SUCCESS,
            reference_number=TransactionService.generate_reference(),
            description=description
        )
        NotificationService.send_template(
            actor,
            NotificationTemplates.TRANSFER_SUCCESS,
            amount=amount
        )
        AuditLogService.info(
            actor=actor,
            action="TRANSFER_SUCCESS",
            metadata={"amount": str(amount)}
        )

        NotificationService.send_sms(
            user=actor,
            message=f"Transfer successful. Ref:{txn.reference_number}"
        )

        return txn

    @staticmethod
    @db_transaction.atomic
    def iban_transfer(*, actor, source, destination, amount, ip):

        main_service.check_transaction(
            actor=actor,
            source=source,
            destination=destination,
            amount=amount,
            ip=ip
        )

        fee = Decimal("2")
        total = amount + fee

        if source.balance < total:
            raise Exception("Insufficient balance")

        source.balance -= total
        destination.balance += amount

        source.save(update_fields=["balance"])
        destination.save(update_fields=["balance"])

        txn = Transaction.objects.create(
            account=source,
            amount=amount,
            fee=fee,
            type=TransactionType.IBAN_TRANSFER,
            status=TransactionStatus.SUCCESS,
            reference_number=TransactionService.generate_reference(),
            description="IBAN Transfer"
        )

        AuditLogService.info(
            actor=actor,
            action="IBAN_TRANSFER_SUCCESS",
            metadata={"amount": str(amount)}
        )

        return txn

    @staticmethod
    def get_statement(account):
        return Transaction.objects.filter(account=account)

    @staticmethod
    def loan_disbursement(account, amount, loan):

        return Transaction.objects.create(
            account=account,
            amount=amount,
            fee=0,
            type="LOAN_DISBURSEMENT",
            status="SUCCESS",
            description=f"Loan #{loan.id}"
        )

    @staticmethod
    def installment_payment(account, amount, installment):

        return Transaction.objects.create(
            account=account,
            amount=amount,
            fee=0,
            type="INSTALLMENT_PAYMENT",
            status="SUCCESS",
            description=f"Installment #{installment.id}"
        )

    @staticmethod
    def late_fee(account, amount, loan):

        return Transaction.objects.create(
            account=account,
            amount=amount,
            fee=0,
            type="LATE_FEE",
            status="SUCCESS",
            description=f"Loan penalty #{loan.id}"
        )
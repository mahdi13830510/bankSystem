from uuid import uuid4
from decimal import Decimal

from django.db import transaction as db_transaction

from apps.auditlogs.services import AuditLogService
from apps.notifications.services import NotificationService
from apps.notifications.templates import NotificationTemplates
from apps.fraud.services.main_service import FraudService
from apps.transactions.core_services import LimitService

from .models import (
    Transaction,
    TransactionType,
    TransactionStatus,
)


class TransactionService:

    @staticmethod
    def generate_reference():
        return uuid4().hex[:24].upper()

    # ==========================================
    # CARD TO CARD TRANSFER
    # ==========================================
    @staticmethod
    @db_transaction.atomic
    def card_transfer(
        *,
        actor,
        source,
        destination,
        amount,
        ip,
        description=""
    ):

        amount = Decimal(str(amount))

        # daily limit
        LimitService.validate_daily_transfer_limit(
            account=source,
            amount=amount
        )

        fee = Decimal(str(destination.bank.transfer_fee))
        total = amount + fee

        if source.balance < total:
            raise Exception("Insufficient balance")

        # create pending transaction first
        txn = Transaction.objects.create(
            account=source,
            amount=amount,
            fee=fee,
            type=TransactionType.CARD_TO_CARD,
            status=TransactionStatus.PENDING,
            reference_number=TransactionService.generate_reference(),
            description=description,
        )

        # ===============================
        # FRAUD CHECK (MATCH YOUR SERVICE)
        # ===============================
        fraud_report = FraudService.check_transaction(
            user=actor,
            transaction=txn,
            ip=ip
        )

        # apply balances after fraud pass
        source.balance -= total
        destination.balance += amount

        source.save(update_fields=["balance"])
        destination.save(update_fields=["balance"])

        txn.status = TransactionStatus.SUCCESS
        txn.save(update_fields=["status"])

        NotificationService.send_template(
            actor,
            NotificationTemplates.TRANSFER_SUCCESS,
            amount=amount
        )

        AuditLogService.info(
            actor=actor,
            action="TRANSFER_SUCCESS",
            metadata={
                "transaction_id": str(txn.id),
                "amount": str(amount),
                "risk_score": fraud_report.score,
            }
        )

        return txn

    # ==========================================
    # IBAN TRANSFER
    # ==========================================
    @staticmethod
    @db_transaction.atomic
    def iban_transfer(
        *,
        actor,
        source,
        destination,
        amount,
        ip
    ):

        amount = Decimal(str(amount))
        fee = Decimal("2.00")
        total = amount + fee

        if source.balance < total:
            raise Exception("Insufficient balance")

        txn = Transaction.objects.create(
            account=source,
            amount=amount,
            fee=fee,
            type=TransactionType.IBAN_TRANSFER,
            status=TransactionStatus.PENDING,
            reference_number=TransactionService.generate_reference(),
            description="IBAN Transfer",
        )

        FraudService.check_transaction(
            user=actor,
            transaction=txn,
            ip=ip
        )

        source.balance -= total
        destination.balance += amount

        source.save(update_fields=["balance"])
        destination.save(update_fields=["balance"])

        txn.status = TransactionStatus.SUCCESS
        txn.save(update_fields=["status"])

        AuditLogService.info(
            actor=actor,
            action="IBAN_TRANSFER_SUCCESS",
            metadata={
                "transaction_id": str(txn.id),
                "amount": str(amount)
            }
        )

        return txn

    # ==========================================
    # STATEMENT
    # ==========================================
    @staticmethod
    def get_statement(account):
        return Transaction.objects.filter(account=account).order_by("-created_at")

    # ==========================================
    # LOAN DISBURSEMENT
    # ==========================================
    @staticmethod
    def loan_disbursement(account, amount, loan):

        return Transaction.objects.create(
            account=account,
            amount=amount,
            fee=Decimal("0"),
            type=TransactionType.LOAN_DISBURSEMENT,
            status=TransactionStatus.SUCCESS,
            reference_number=TransactionService.generate_reference(),
            description=f"Loan #{loan.id}"
        )

    # ==========================================
    # INSTALLMENT PAYMENT
    # ==========================================
    @staticmethod
    def installment_payment(account, amount, installment):

        return Transaction.objects.create(
            account=account,
            amount=amount,
            fee=Decimal("0"),
            type=TransactionType.INSTALLMENT_PAYMENT,
            status=TransactionStatus.SUCCESS,
            reference_number=TransactionService.generate_reference(),
            description=f"Installment #{installment.id}"
        )

    # ==========================================
    # LATE FEE
    # ==========================================
    @staticmethod
    def late_fee(account, amount, loan):

        return Transaction.objects.create(
            account=account,
            amount=amount,
            fee=Decimal("0"),
            type=TransactionType.LATE_FEE,
            status=TransactionStatus.SUCCESS,
            reference_number=TransactionService.generate_reference(),
            description=f"Loan penalty #{loan.id}"
        )
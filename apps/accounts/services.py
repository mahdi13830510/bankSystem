import random
from decimal import Decimal

from django.db import transaction
from django.core.exceptions import ValidationError

from apps.banks.models import Bank
from .models import Account, AccountStatus
from ..auditlogs.services import AuditLogService


class AccountService:

    @staticmethod
    def generate_account_number():
        while True:
            value = "".join(random.choices("0123456789", k=16))
            if not Account.objects.filter(account_number=value).exists():
                return value

    @staticmethod
    def generate_iban():
        while True:
            body = "".join(random.choices("0123456789", k=24))
            iban = f"TR{body}"
            if not Account.objects.filter(iban=iban).exists():
                return iban

    @staticmethod
    def my_accounts(user):
        return Account.objects.filter(customer=user)

    @staticmethod
    def get_owned(user, account_id):
        return Account.objects.get(id=account_id, customer=user)

    @staticmethod
    def get_by_id(account_id):
        return Account.objects.get(id=account_id)

    @staticmethod
    def get_by_number(account_number):
        return Account.objects.get(account_number=account_number)

    @staticmethod
    def get_by_iban(iban):
        return Account.objects.get(iban=iban)

    @staticmethod
    def open_account(user, bank_id, type, currency):
        bank = Bank.objects.get(id=bank_id)

        account = Account.objects.create(
            customer=user,
            bank=bank,
            account_number=AccountService.generate_account_number(),
            iban=AccountService.generate_iban(),
            type=type,
            currency=currency
        )

        AuditLogService.info(
            actor=user,
            action="ACCOUNT_CREATED"
        )

        return account

    @staticmethod
    @transaction.atomic
    def increase_balance(account_id, amount, actor=None):
        account = Account.objects.select_for_update().get(id=account_id)

        amount = Decimal(amount)
        if amount <= 0:
            raise ValidationError("Invalid amount")

        account.balance += amount
        account.save(update_fields=["balance"])
        AuditLogService.info(
            actor=actor,
            action="BALANCE_INCREASED"
        )

        return account

    @staticmethod
    @transaction.atomic
    def decrease_balance(account_id, amount):
        account = Account.objects.select_for_update().get(id=account_id)

        amount = Decimal(amount)

        if amount <= 0:
            raise ValidationError("Invalid amount")

        if account.status != AccountStatus.ACTIVE:
            raise ValidationError("Account is not active")

        if account.available_balance < amount:
            raise ValidationError("Insufficient balance")

        account.balance -= amount
        account.save(update_fields=["balance"])

        return account

    @staticmethod
    @transaction.atomic
    def block_balance(account_id, amount, actor=None):
        account = Account.objects.select_for_update().get(id=account_id)

        amount = Decimal(amount)

        if amount <= 0:
            raise ValidationError("Invalid amount")

        if account.available_balance < amount:
            raise ValidationError("Insufficient available balance")

        account.blocked_balance += amount
        account.save(update_fields=["blocked_balance"])
        AuditLogService.info(
            actor=actor,
            action="BALANCE_DECREASED"
        )

        return account

    @staticmethod
    @transaction.atomic
    def unblock_balance(account_id, amount, actor=None):
        account = Account.objects.select_for_update().get(id=account_id)

        amount = Decimal(amount)

        if amount <= 0:
            raise ValidationError("Invalid amount")

        if account.blocked_balance < amount:
            raise ValidationError("Blocked balance insufficient")

        account.blocked_balance -= amount
        account.save(update_fields=["blocked_balance"])
        AuditLogService.info(
            actor=actor,
            action="BALANCE_UNBLOCKED"
        )

        return account

    @staticmethod
    def freeze(account_id, actor=None):
        account = Account.objects.get(id=account_id)
        account.status = AccountStatus.BLOCKED
        account.save(update_fields=["status"])
        AuditLogService.info(
            actor=actor,
            action="ACCOUNT_FREEZE"
        )

        return account

    @staticmethod
    def activate(account_id, actor=None):
        account = Account.objects.get(id=account_id)
        account.status = AccountStatus.ACTIVE
        account.save(update_fields=["status"])
        AuditLogService.info(
            actor=actor,
            action="ACCOUNT_ACTIVATED"
        )

        return account

    @staticmethod
    def close(account_id,actor=None):
        account = Account.objects.get(id=account_id)

        if account.balance > 0:
            raise ValidationError("Balance must be zero")

        account.status = AccountStatus.CLOSED
        account.save(update_fields=["status"])
        AuditLogService.info(
            actor=actor,
            action="ACCOUNT_CLOSED"
        )

        return account

    @staticmethod
    def get_primary_account(user):
        return Account.objects.get(
            customer=user,
            is_primary=True,
            status="ACTIVE"
        )

    @staticmethod
    def block_for_loan(account, amount):
        account.loan_blocked_balance += amount
        account.save(update_fields=["loan_blocked_balance"])

    @staticmethod
    def unblock_loan(account, amount):
        account.loan_blocked_balance -= amount
        if account.loan_blocked_balance < 0:
            account.loan_blocked_balance = 0

        account.save(update_fields=["loan_blocked_balance"])


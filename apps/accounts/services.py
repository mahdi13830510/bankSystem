import random
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError

from apps.banks.models import Bank
from .models import Account, AccountStatus


class AccountService:

    # -----------------------------
    # GENERATORS
    # -----------------------------

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

    # -----------------------------
    # CREATE
    # -----------------------------

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

        # auditlog hook
        # AuditLogService.log(...)

        return account

    # -----------------------------
    # READ
    # -----------------------------

    @staticmethod
    def my_accounts(user):
        return Account.objects.filter(customer=user)

    @staticmethod
    def get_owned(user, account_id):
        return Account.objects.get(id=account_id, customer=user)

    @staticmethod
    def get_admin(account_id):
        return Account.objects.get(id=account_id)

    # -----------------------------
    # MONEY OPS
    # -----------------------------

    @staticmethod
    @transaction.atomic
    def deposit(account_id, amount):
        acc = Account.objects.select_for_update().get(id=account_id)

        acc.balance += Decimal(amount)
        acc.save(update_fields=["balance"])

        return acc

    @staticmethod
    @transaction.atomic
    def withdraw(account_id, amount):
        acc = Account.objects.select_for_update().get(id=account_id)

        amount = Decimal(amount)

        if acc.status != AccountStatus.ACTIVE:
            raise ValidationError("Account blocked")

        if acc.available_balance < amount:
            raise ValidationError("Insufficient balance")

        acc.balance -= amount
        acc.save(update_fields=["balance"])

        return acc

    @staticmethod
    @transaction.atomic
    def block_amount(account_id, amount):
        acc = Account.objects.select_for_update().get(id=account_id)

        amount = Decimal(amount)

        if acc.available_balance < amount:
            raise ValidationError("Insufficient available balance")

        acc.blocked_balance += amount
        acc.save(update_fields=["blocked_balance"])

        return acc

    @staticmethod
    @transaction.atomic
    def unblock_amount(account_id, amount):
        acc = Account.objects.select_for_update().get(id=account_id)

        amount = Decimal(amount)

        if acc.blocked_balance < amount:
            raise ValidationError("Blocked balance too low")

        acc.blocked_balance -= amount
        acc.save(update_fields=["blocked_balance"])

        return acc

    # -----------------------------
    # STATUS OPS
    # -----------------------------

    @staticmethod
    def freeze(account_id):
        acc = Account.objects.get(id=account_id)
        acc.status = AccountStatus.BLOCKED
        acc.save(update_fields=["status"])
        return acc

    @staticmethod
    def close(account_id):
        acc = Account.objects.get(id=account_id)

        if acc.balance > 0:
            raise ValidationError("Balance must be zero")

        acc.status = AccountStatus.CLOSED
        acc.save(update_fields=["status"])

        return acc

    # -----------------------------
    # INTEGRATION
    # -----------------------------

    @staticmethod
    def transaction_debit(account_id, amount):
        return AccountService.withdraw(account_id, amount)

    @staticmethod
    def transaction_credit(account_id, amount):
        return AccountService.deposit(account_id, amount)

    @staticmethod
    def reserve_installment(account_id, amount):
        return AccountService.block_amount(account_id, amount)

    @staticmethod
    def pay_installment(account_id, amount):
        return AccountService.withdraw(account_id, amount)
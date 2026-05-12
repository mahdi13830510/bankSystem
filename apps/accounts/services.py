from django.db import transaction
from .models import Account, AccountStatus


@transaction.atomic
def deposit(account: Account, amount):
    if amount <= 0:
        raise ValueError("Amount must be positive.")
    account.balance += amount
    account.save(update_fields=["balance"])


@transaction.atomic
def withdraw(account: Account, amount):
    if amount <= 0:
        raise ValueError("Amount must be positive.")
    if not account.can_withdraw(amount):
        raise ValueError("Insufficient available balance.")
    account.balance -= amount
    account.save(update_fields=["balance"])


@transaction.atomic
def block_amount(account: Account, amount):
    if amount <= 0:
        raise ValueError("Amount must be positive.")
    if account.available_balance < amount:
        raise ValueError("Insufficient available balance.")
    account.blocked_balance += amount
    account.save(update_fields=["blocked_balance"])


@transaction.atomic
def unblock_amount(account: Account, amount):
    if amount <= 0:
        raise ValueError("Amount must be positive.")
    if account.blocked_balance < amount:
        raise ValueError("Blocked balance is not enough.")
    account.blocked_balance -= amount
    account.save(update_fields=["blocked_balance"])


@transaction.atomic
def close_account(account: Account):
    if account.balance != 0 or account.blocked_balance != 0:
        raise ValueError("Account cannot be closed while balance exists.")
    account.status = AccountStatus.CLOSED
    account.save(update_fields=["status"])

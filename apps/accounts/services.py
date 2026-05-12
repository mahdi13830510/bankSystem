from django.db import transaction
from django.utils import timezone
from .models import Account, AccountStatus, AccountOwnershipHistory
from .exceptions import InsufficientBalanceError, InvalidAmountError
from apps.transactions.services import create_financial_entry
from apps.transactions.models import TransactionType


@transaction.atomic
def create_account(customer, bank, account_type, currency, initial_balance=0, created_by=None):
    from .generators import generate_account_number, generate_iban
    from .validators import validate_unique_account_type_per_bank_customer

    validate_unique_account_type_per_bank_customer(customer, bank, account_type)

    account = Account.objects.create(
        customer=customer,
        bank=bank,
        type=account_type,
        currency=currency,
        account_number=generate_account_number(),
        iban=generate_iban(getattr(bank, "bank_code", "IR")),
        balance=initial_balance,
        blocked_balance=0,
        status=AccountStatus.ACTIVE,
    )
    return account


@transaction.atomic
def freeze_account(account: Account):
    account.status = AccountStatus.FROZEN
    account.save(update_fields=["status"])
    return account


@transaction.atomic
def unfreeze_account(account: Account):
    account.status = AccountStatus.ACTIVE
    account.save(update_fields=["status"])
    return account


@transaction.atomic
def soft_delete_account(account: Account):
    account.soft_delete()
    return account


@transaction.atomic
def deposit(account: Account, amount, performed_by, reference=None, description="Deposit"):
    if amount <= 0:
        raise InvalidAmountError("Amount must be positive.")

    account.balance += amount
    account.save(update_fields=["balance"])

    tx = create_financial_entry(
        destination_account=account,
        amount=amount,
        transaction_type=TransactionType.CREDIT,
        performed_by=performed_by,
        description=description,
        reference=reference,
    )
    return account, tx


@transaction.atomic
def withdraw(account: Account, amount, performed_by, reference=None, description="Withdraw"):
    if amount <= 0:
        raise InvalidAmountError("Amount must be positive.")
    if account.available_balance < amount:
        raise InsufficientBalanceError("Insufficient available balance.")

    account.balance -= amount
    account.save(update_fields=["balance"])

    tx = create_financial_entry(
        source_account=account,
        amount=amount,
        transaction_type=TransactionType.DEBIT,
        performed_by=performed_by,
        description=description,
        reference=reference,
    )
    return account, tx


@transaction.atomic
def block_amount(account: Account, amount):
    if amount <= 0:
        raise InvalidAmountError("Amount must be positive.")
    if account.available_balance < amount:
        raise InsufficientBalanceError("Insufficient available balance.")
    account.blocked_balance += amount
    account.save(update_fields=["blocked_balance"])
    return account


@transaction.atomic
def unblock_amount(account: Account, amount):
    if amount <= 0:
        raise InvalidAmountError("Amount must be positive.")
    if account.blocked_balance < amount:
        raise InsufficientBalanceError("Blocked balance is not enough.")
    account.blocked_balance -= amount
    account.save(update_fields=["blocked_balance"])
    return account


@transaction.atomic
def change_account_owner(account: Account, new_customer, changed_by, note=""):
    old_customer = account.customer
    account.customer = new_customer
    account.save(update_fields=["customer"])

    AccountOwnershipHistory.objects.create(
        account=account,
        old_customer=old_customer,
        new_customer=new_customer,
        changed_by=changed_by,
        note=note,
    )
    return account

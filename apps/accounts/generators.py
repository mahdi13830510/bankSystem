import random
import string

from .models import Account


def generate_account_number():
    while True:
        number = "".join(random.choices(string.digits, k=13))
        if not Account.objects.filter(account_number=number).exists():
            return number


def generate_iban(bank_code="IR"):
    while True:
        body = "".join(random.choices(string.digits, k=24))
        iban = f"{bank_code}{body}"
        if not Account.objects.filter(iban=iban).exists():
            return iban

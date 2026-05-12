from rest_framework import serializers
from .models import Account


def validate_unique_account_type_per_bank_customer(customer, bank, account_type, instance=None):
    qs = Account.objects.filter(customer=customer, bank=bank, type=account_type)
    if instance:
        qs = qs.exclude(pk=instance.pk)
    if qs.exists():
        raise serializers.ValidationError(
            "This customer already has an account of this type in this bank."
        )

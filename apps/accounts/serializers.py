from decimal import Decimal

from rest_framework import serializers
from .models import Account, AccountType, AccountStatus, CurrencyType


# ─────────────────────────────────────────
#  Read Serializers
# ─────────────────────────────────────────

class AccountSerializer(serializers.ModelSerializer):
    """for customer    """
    available_balance = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = Account
        fields = [
            "id",
            "customer",
            "bank",
            "account_number",
            "iban",
            "type",
            "currency",
            "balance",
            "blocked_balance",
            "loan_blocked_balance",
            "available_balance",
            "status",
            "is_primary",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "customer",
            "account_number",
            "iban",
            "balance",
            "blocked_balance",
            "loan_blocked_balance",
            "status",
            "created_at",
        ]


class AccountDetailSerializer(serializers.ModelSerializer):
    """for admin  """
    available_balance = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        read_only=True,
    )
    customer_name = serializers.CharField(
        source="customer.fullname",
        read_only=True,
    )
    customer_phone = serializers.CharField(
        source="customer.phone",
        read_only=True,
    )
    bank_name = serializers.CharField(
        source="bank.name",
        read_only=True,
    )

    class Meta:
        model = Account
        fields = [
            "id",
            "customer",
            "customer_name",
            "customer_phone",
            "bank",
            "bank_name",
            "account_number",
            "iban",
            "type",
            "currency",
            "balance",
            "blocked_balance",
            "loan_blocked_balance",
            "available_balance",
            "status",
            "is_primary",
            "created_at",
        ]
        read_only_fields = fields


# ─────────────────────────────────────────
#  Write Serializers — Customer
# ─────────────────────────────────────────

class OpenAccountSerializer(serializers.Serializer):
    bank_id = serializers.UUIDField()
    type = serializers.ChoiceField(choices=AccountType.choices)
    currency = serializers.ChoiceField(choices=CurrencyType.choices)


# ─────────────────────────────────────────
#  Write Serializers — Admin / Staff
# ─────────────────────────────────────────

class AdminOpenAccountSerializer(serializers.Serializer):
    """admin: open account for one special customer"""
    customer_id = serializers.IntegerField()
    bank_id = serializers.UUIDField()
    type = serializers.ChoiceField(choices=AccountType.choices)
    currency = serializers.ChoiceField(choices=CurrencyType.choices)
    is_primary = serializers.BooleanField(default=False)


class AmountSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=18, decimal_places=2, min_value=Decimal("0.01")
    )


class AdminBalanceAdjustSerializer(serializers.Serializer):
    """admin: block / unblock balance """
    amount = serializers.DecimalField(
        max_digits=18, decimal_places=2, min_value=Decimal("0.01")
    )
    reason = serializers.CharField(
        max_length=500, required=False, allow_blank=True
    )


class AdminAccountFilterSerializer(serializers.Serializer):
    """query params for admin list"""
    customer_id = serializers.IntegerField(required=False)
    bank_id = serializers.UUIDField(required=False)
    status = serializers.ChoiceField(
        choices=AccountStatus.choices, required=False
    )
    type = serializers.ChoiceField(
        choices=AccountType.choices, required=False
    )
    currency = serializers.ChoiceField(
        choices=CurrencyType.choices, required=False
    )
    is_primary = serializers.BooleanField(required=False)
    search = serializers.CharField(
        required=False,
        help_text="search at account_number / iban",
    )
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)

from rest_framework import serializers
from .models import Account


class AccountSerializer(serializers.ModelSerializer):
    available_balance = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        read_only=True
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
            "available_balance",
            "status",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "customer",
            "account_number",
            "iban",
            "balance",
            "blocked_balance",
            "status",
            "created_at",
        ]


class OpenAccountSerializer(serializers.Serializer):
    bank_id = serializers.IntegerField()
    type = serializers.CharField()
    currency = serializers.CharField()


class AmountSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)
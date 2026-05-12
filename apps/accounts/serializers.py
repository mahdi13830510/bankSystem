from rest_framework import serializers
from .models import Account, AccountStatus, AccountType, CurrencyType


class AccountSerializer(serializers.ModelSerializer):
    available_balance = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)

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
        read_only_fields = ["id", "created_at", "available_balance"]

    def validate(self, attrs):
        balance = attrs.get("balance", getattr(self.instance, "balance", 0))
        blocked_balance = attrs.get("blocked_balance", getattr(self.instance, "blocked_balance", 0))

        if blocked_balance > balance:
            raise serializers.ValidationError("blocked_balance cannot be greater than balance.")

        return attrs


class AccountCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = [
            "customer",
            "bank",
            "account_number",
            "iban",
            "type",
            "currency",
            "balance",
            "blocked_balance",
            "status",
        ]

    def validate(self, attrs):
        if attrs.get("blocked_balance", 0) > attrs.get("balance", 0):
            raise serializers.ValidationError("blocked_balance cannot be greater than balance.")
        return attrs


class AccountUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = [
            "type",
            "currency",
            "balance",
            "blocked_balance",
            "status",
        ]

    def validate(self, attrs):
        balance = attrs.get("balance", getattr(self.instance, "balance", 0))
        blocked_balance = attrs.get("blocked_balance", getattr(self.instance, "blocked_balance", 0))
        if blocked_balance > balance:
            raise serializers.ValidationError("blocked_balance cannot be greater than balance.")
        return attrs

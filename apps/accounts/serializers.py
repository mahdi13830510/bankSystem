from rest_framework import serializers
from .models import Account, AccountOwnershipHistory
from .validators import validate_unique_account_type_per_bank_customer


class AccountSerializer(serializers.ModelSerializer):
    available_balance = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)

    class Meta:
        model = Account
        fields = [
            "id", "customer", "bank", "account_number", "iban", "type",
            "currency", "balance", "blocked_balance", "available_balance",
            "status", "created_at", "deleted_at",
        ]
        read_only_fields = ["id", "account_number", "iban", "created_at", "deleted_at", "available_balance"]

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        customer = attrs.get("customer", getattr(instance, "customer", None))
        bank = attrs.get("bank", getattr(instance, "bank", None))
        account_type = attrs.get("type", getattr(instance, "type", None))

        if customer and bank and account_type:
            validate_unique_account_type_per_bank_customer(customer, bank, account_type, instance=instance)

        balance = attrs.get("balance", getattr(instance, "balance", 0))
        blocked_balance = attrs.get("blocked_balance", getattr(instance, "blocked_balance", 0))
        if blocked_balance > balance:
            raise serializers.ValidationError("blocked_balance cannot be greater than balance.")

        return attrs


class AccountCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ["customer", "bank", "type", "currency", "balance"]

    def validate(self, attrs):
        validate_unique_account_type_per_bank_customer(
            attrs["customer"], attrs["bank"], attrs["type"]
        )
        return attrs


class FreezeUnfreezeSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)


class AmountSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=0.01)


class ChangeOwnerSerializer(serializers.Serializer):
    new_customer = serializers.IntegerField()
    note = serializers.CharField(required=False, allow_blank=True)


class OwnershipHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountOwnershipHistory
        fields = "__all__"

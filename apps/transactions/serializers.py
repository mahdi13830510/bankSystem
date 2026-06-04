from rest_framework import serializers
from .models import Transaction, TransactionType, TransactionStatus


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = [
            "id",
            "account",
            "amount",
            "fee",
            "type",
            "status",
            "reference_number",
            "description",
            "created_at",
        ]


class TransactionDetailSerializer(serializers.ModelSerializer):
    account_number = serializers.CharField(
        source="account.account_number", read_only=True
    )
    customer_id = serializers.IntegerField(
        source="account.customer_id", read_only=True
    )
    customer_name = serializers.CharField(
        source="account.customer.fullname", read_only=True
    )

    class Meta:
        model = Transaction
        fields = [
            "id",
            "account",
            "account_number",
            "customer_id",
            "customer_name",
            "amount",
            "fee",
            "type",
            "status",
            "reference_number",
            "description",
            "created_at",
        ]


class CardTransferSerializer(serializers.Serializer):
    source_account_id = serializers.IntegerField()
    destination_account_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    description = serializers.CharField(required=False, allow_blank=True)


class IbanTransferSerializer(serializers.Serializer):
    source_account_id = serializers.UUIDField()
    destination_iban = serializers.CharField()
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)


class ReverseTransactionSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500)


class AdminTransactionFilterSerializer(serializers.Serializer):
    account_id = serializers.IntegerField(required=False)
    type = serializers.ChoiceField(
        choices=TransactionType.choices, required=False
    )
    status = serializers.ChoiceField(
        choices=TransactionStatus.choices, required=False
    )
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    reference_number = serializers.CharField(required=False)

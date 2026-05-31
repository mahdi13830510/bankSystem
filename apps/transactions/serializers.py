from rest_framework import serializers
from .models import Transaction


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
            "created_at"
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
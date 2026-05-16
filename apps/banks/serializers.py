from rest_framework import serializers
from .models import Bank, Branch


class BankSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bank
        fields = [
            "id",
            "name",
            "code",
            "iban_prefix",
            "swift_code",
            "transfer_fee",
            "status",
            "supports_instant_transfer",
            "created_at"
        ]


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = [
            "id",
            "bank",
            "name",
            "code",
            "city",
            "address",
            "phone",
            "is_active"
        ]

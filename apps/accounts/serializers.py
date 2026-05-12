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
        fields = "__all__"


class OpenAccountSerializer(serializers.Serializer):
    bank_id = serializers.IntegerField()
    type = serializers.CharField()
    currency = serializers.CharField()


class AmountSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)
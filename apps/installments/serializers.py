from rest_framework import serializers
from .models import Installment


class InstallmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Installment
        fields = [
            "id",
            "loan",
            "number",
            "due_date",
            "amount",
            "paid_amount",
            "penalty_amount",
            "status",
            "paid_at",
            "created_at"
        ]

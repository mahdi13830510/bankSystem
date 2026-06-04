from rest_framework import serializers
from .models import Installment, InstallmentStatus


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
            "created_at",
        ]


class InstallmentDetailSerializer(serializers.ModelSerializer):
    customer_id = serializers.IntegerField(
        source="loan.customer_id", read_only=True
    )
    customer_name = serializers.CharField(
        source="loan.customer.fullname", read_only=True
    )

    class Meta:
        model = Installment
        fields = [
            "id",
            "loan",
            "customer_id",
            "customer_name",
            "number",
            "due_date",
            "amount",
            "paid_amount",
            "penalty_amount",
            "status",
            "paid_at",
            "created_at",
        ]


class AdminInstallmentFilterSerializer(serializers.Serializer):
    loan_id = serializers.UUIDField(required=False)
    status = serializers.ChoiceField(
        choices=InstallmentStatus.choices, required=False
    )
    due_date_from = serializers.DateField(required=False)
    due_date_to = serializers.DateField(required=False)
    customer_id = serializers.IntegerField(required=False)


class ManualPenaltySerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=18, decimal_places=2, min_value=0
    )
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)

from rest_framework import serializers
from .models import LoanRequest, Loan


class LoanRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanRequest
        exclude = ["customer", "status", "risk_score", "manager_note"]


class LoanRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanRequest
        fields = [
            "id",
            "customer",
            "amount",
            "duration_months",
            "loan_type",
            "monthly_income",
            "existing_debt",
            "status",
            "risk_score",
            "manager_note",
            "created_at"
        ]


class LoanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loan
        fields = [
            "id",
            "customer",
            "loan_request",
            "principal_amount",
            "interest_rate",
            "total_payable",
            "monthly_installment",
            "duration_months",
            "paid_amount",
            "status",
            "started_at"
        ]

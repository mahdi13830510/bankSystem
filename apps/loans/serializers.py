from rest_framework import serializers
from .models import LoanRequest, Loan, LoanStatus, LoanRequestStatus


class LoanRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanRequest
        exclude = ["customer", "status", "risk_score", "manager_note"]


class LoanRequestSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source="customer.fullname", read_only=True
    )

    class Meta:
        model = LoanRequest
        fields = [
            "id",
            "customer",
            "customer_name",
            "amount",
            "duration_months",
            "loan_type",
            "monthly_income",
            "existing_debt",
            "status",
            "risk_score",
            "manager_note",
            "created_at",
        ]


class LoanSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source="customer.fullname", read_only=True
    )

    class Meta:
        model = Loan
        fields = [
            "id",
            "customer",
            "customer_name",
            "loan_request",
            "principal_amount",
            "interest_rate",
            "total_payable",
            "monthly_installment",
            "duration_months",
            "paid_amount",
            "status",
            "started_at",
        ]


class RejectLoanSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000)


class ChangeLoanStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            LoanStatus.COMPLETED,
            LoanStatus.DEFAULTED,
            LoanStatus.CLOSED,
        ]
    )
    note = serializers.CharField(max_length=1000, required=False, allow_blank=True)


class AdminLoanRequestFilterSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=LoanRequestStatus.choices, required=False
    )
    loan_type = serializers.CharField(required=False)
    customer_id = serializers.IntegerField(required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)


class AdminLoanFilterSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=LoanStatus.choices, required=False
    )
    customer_id = serializers.IntegerField(required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)

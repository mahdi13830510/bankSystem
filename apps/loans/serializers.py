from rest_framework import serializers
from .models import LoanRequest, Loan


class LoanRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanRequest
        exclude = ["customer", "status", "risk_score", "manager_note"]


class LoanRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanRequest
        fields = "__all__"


class LoanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loan
        fields = "__all__"
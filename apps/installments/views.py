from django.shortcuts import get_object_or_404

from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import status

from apps.loans.models import Loan

from .models import Installment
from .serializers import (
    InstallmentSerializer,
    InstallmentDetailSerializer,
    AdminInstallmentFilterSerializer,
    ManualPenaltySerializer,
)
from .services import InstallmentService


# ─────────────────────────────────────────
#  Customer endpoints
# ─────────────────────────────────────────

class MyInstallmentsView(ListAPIView):
    serializer_class = InstallmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Installment.objects.filter(
            loan__customer=self.request.user
        )


class MyInstallmentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        installment = get_object_or_404(
            Installment,
            pk=pk,
            loan__customer=request.user,
        )
        return Response(InstallmentSerializer(installment).data)


class MyLoanInstallmentsView(ListAPIView):
    serializer_class = InstallmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        loan = get_object_or_404(
            Loan,
            pk=self.kwargs["loan_id"],
            customer=self.request.user,
        )
        return Installment.objects.filter(loan=loan)


class PayInstallmentView(APIView):
    """pay one installment (+ ownership check)"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        installment = get_object_or_404(
            Installment,
            pk=pk,
            loan__customer=request.user,
        )
        InstallmentService.pay_installment(request.user, installment)
        return Response({"detail": "paid"})


class RemainingDebtView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, loan_id):
        loan = get_object_or_404(
            Loan,
            pk=loan_id,
            customer=request.user,
        )
        debt = InstallmentService.remaining_debt(loan)
        return Response({"remaining_debt": str(debt)})


# ─────────────────────────────────────────
#  Admin / Staff endpoints
# ─────────────────────────────────────────

class AdminInstallmentListView(ListAPIView):
    """
    filter: loan_id,status,due_date_from,due_date_to,&customer_id
    """
    serializer_class = InstallmentDetailSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        params = AdminInstallmentFilterSerializer(
            data=self.request.query_params
        )
        params.is_valid(raise_exception=True)
        f = params.validated_data

        qs = Installment.objects.select_related(
            "loan__customer"
        ).all()

        if f.get("loan_id"):
            qs = qs.filter(loan_id=f["loan_id"])
        if f.get("status"):
            qs = qs.filter(status=f["status"])
        if f.get("due_date_from"):
            qs = qs.filter(due_date__gte=f["due_date_from"])
        if f.get("due_date_to"):
            qs = qs.filter(due_date__lte=f["due_date_to"])
        if f.get("customer_id"):
            qs = qs.filter(loan__customer_id=f["customer_id"])

        return qs


class AdminInstallmentDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        installment = get_object_or_404(
            Installment.objects.select_related("loan__customer"), pk=pk
        )
        return Response(InstallmentDetailSerializer(installment).data)


class AdminLoanInstallmentsView(ListAPIView):
    """installment view of one special loan"""
    serializer_class = InstallmentDetailSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return Installment.objects.filter(
            loan_id=self.kwargs["loan_id"]
        ).select_related("loan__customer")


class AdminOverdueInstallmentsView(ListAPIView):
    serializer_class = InstallmentDetailSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return Installment.objects.filter(
            status="OVERDUE"
        ).select_related("loan__customer").order_by("due_date")


class AdminApplyPenaltyView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        serializer = ManualPenaltySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        installment = get_object_or_404(Installment, pk=pk)

        try:
            updated = InstallmentService.apply_manual_penalty(
                installment=installment,
                amount=serializer.validated_data["amount"],
                actor=request.user,
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(InstallmentDetailSerializer(updated).data)


class AdminRemainingDebtView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, loan_id):
        loan = get_object_or_404(Loan, pk=loan_id)
        debt = InstallmentService.remaining_debt(loan)
        return Response({
            "loan_id": str(loan.id),
            "remaining_debt": str(debt),
        })
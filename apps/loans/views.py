from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import status

from .models import LoanRequest, Loan
from .serializers import (
    LoanRequestCreateSerializer,
    LoanRequestSerializer,
    LoanSerializer,
    RejectLoanSerializer,
    ChangeLoanStatusSerializer,
    AdminLoanRequestFilterSerializer,
    AdminLoanFilterSerializer,
)
from .services import LoanService


# ─────────────────────────────────────────
#  Customer endpoints
# ─────────────────────────────────────────

class LoanRequestCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LoanRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        req = LoanService.create_request(
            request.user,
            serializer.validated_data,
        )

        return Response(
            LoanRequestSerializer(req).data,
            status=status.HTTP_201_CREATED,
        )


class MyLoanRequestsView(ListAPIView):
    serializer_class = LoanRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return LoanRequest.objects.filter(
            customer=self.request.user
        ).order_by("-created_at")


class MyLoanRequestDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        req = get_object_or_404(
            LoanRequest, pk=pk, customer=request.user
        )
        return Response(LoanRequestSerializer(req).data)


class MyLoansView(ListAPIView):
    """active loans list"""
    serializer_class = LoanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Loan.objects.filter(
            customer=self.request.user
        ).order_by("-started_at")


class MyLoanDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        loan = get_object_or_404(
            Loan, pk=pk, customer=request.user
        )
        return Response(LoanSerializer(loan).data)


# ─────────────────────────────────────────
#  Admin / Staff endpoints
# ─────────────────────────────────────────

class AdminLoanRequestListView(ListAPIView):
    """
    filter: status,loan_type,customer_id,date_from,date_to
    """
    serializer_class = LoanRequestSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        params = AdminLoanRequestFilterSerializer(
            data=self.request.query_params
        )
        params.is_valid(raise_exception=True)
        f = params.validated_data

        qs = LoanRequest.objects.select_related("customer").all()

        if f.get("status"):
            qs = qs.filter(status=f["status"])
        if f.get("loan_type"):
            qs = qs.filter(loan_type=f["loan_type"])
        if f.get("customer_id"):
            qs = qs.filter(customer_id=f["customer_id"])
        if f.get("date_from"):
            qs = qs.filter(created_at__date__gte=f["date_from"])
        if f.get("date_to"):
            qs = qs.filter(created_at__date__lte=f["date_to"])

        return qs.order_by("-created_at")


class AdminLoanRequestDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        req = get_object_or_404(
            LoanRequest.objects.select_related("customer"), pk=pk
        )
        return Response(LoanRequestSerializer(req).data)


class AdminPendingLoansView(ListAPIView):
    serializer_class = LoanRequestSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return LoanRequest.objects.filter(
            status="UNDER_REVIEW"
        ).select_related("customer").order_by("-created_at")


class EvaluateLoanRequestView(APIView):
    """calculate risk score and change status to UNDER_REVIEW"""
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        req = get_object_or_404(LoanRequest, pk=pk)
        score = LoanService.evaluate_request(req)
        return Response({
            "risk_score": score,
            "status": req.status,
        })


class ApproveLoanView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        req = get_object_or_404(LoanRequest, pk=pk)
        loan = LoanService.approve_request(request.user, req)
        return Response(LoanSerializer(loan).data)


class RejectLoanView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        serializer = RejectLoanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        req = get_object_or_404(LoanRequest, pk=pk)
        LoanService.reject_request(
            request.user,
            req,
            serializer.validated_data["reason"],
        )
        return Response({"detail": "rejected"})


class AdminLoanListView(ListAPIView):
    """
    filter: status,customer_id,date_from,date_to
    """
    serializer_class = LoanSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        params = AdminLoanFilterSerializer(
            data=self.request.query_params
        )
        params.is_valid(raise_exception=True)
        f = params.validated_data

        qs = Loan.objects.select_related("customer").all()

        if f.get("status"):
            qs = qs.filter(status=f["status"])
        if f.get("customer_id"):
            qs = qs.filter(customer_id=f["customer_id"])
        if f.get("date_from"):
            qs = qs.filter(started_at__date__gte=f["date_from"])
        if f.get("date_to"):
            qs = qs.filter(started_at__date__lte=f["date_to"])

        return qs.order_by("-started_at")


class AdminLoanDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        loan = get_object_or_404(
            Loan.objects.select_related("customer", "loan_request"), pk=pk
        )
        return Response(LoanSerializer(loan).data)


class AdminChangeLoanStatusView(APIView):
    """change loan status (COMPLETED / DEFAULTED / CLOSED)"""
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        serializer = ChangeLoanStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        loan = get_object_or_404(Loan, pk=pk)
        updated = LoanService.change_status(
            manager=request.user,
            loan=loan,
            new_status=serializer.validated_data["status"],
            note=serializer.validated_data.get("note", ""),
        )
        return Response(LoanSerializer(updated).data)


class AdminCustomerLoansView(ListAPIView):
    """one special customer loans list"""
    serializer_class = LoanSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return Loan.objects.filter(
            customer_id=self.kwargs["customer_id"]
        ).select_related("customer").order_by("-started_at")


class AdminCustomerLoanRequestsView(ListAPIView):
    """one special customer loans request list"""
    serializer_class = LoanRequestSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return LoanRequest.objects.filter(
            customer_id=self.kwargs["customer_id"]
        ).select_related("customer").order_by("-created_at")
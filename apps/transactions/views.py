from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import status

from apps.accounts.models import Account

from .models import Transaction
from .services import TransactionService
from .core_services import LimitService
from .serializers import (
    CardTransferSerializer,
    IbanTransferSerializer,
    TransactionSerializer,
    TransactionDetailSerializer,
    ReverseTransactionSerializer,
    AdminTransactionFilterSerializer,
)


# ─────────────────────────────────────────
#  Customer endpoints
# ─────────────────────────────────────────

class CardTransferView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CardTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        source = get_object_or_404(
            Account,
            id=serializer.validated_data["source_account_id"],
            customer=request.user,
        )
        destination = get_object_or_404(
            Account,
            id=serializer.validated_data["destination_account_id"],
        )

        txn = TransactionService.card_transfer(
            actor=request.user,
            source=source,
            destination=destination,
            amount=serializer.validated_data["amount"],
            ip=request.META.get("REMOTE_ADDR"),
            description=serializer.validated_data.get("description", ""),
        )

        return Response(TransactionSerializer(txn).data)


class IbanTransferView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = IbanTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        source = get_object_or_404(
            Account,
            id=serializer.validated_data["source_account_id"],
            customer=request.user,
        )
        destination = get_object_or_404(
            Account,
            iban=serializer.validated_data["destination_iban"],
        )

        txn = TransactionService.iban_transfer(
            actor=request.user,
            source=source,
            destination=destination,
            amount=serializer.validated_data["amount"],
            ip=request.META.get("REMOTE_ADDR"),
        )

        return Response(TransactionSerializer(txn).data)


class StatementView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, account_id):
        account = get_object_or_404(
            Account,
            id=account_id,
            customer=request.user,
        )
        txns = TransactionService.get_statement(account)
        return Response(TransactionSerializer(txns, many=True).data)


class MyLimitUsageView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, account_id):
        account = get_object_or_404(
            Account,
            id=account_id,
            customer=request.user,
        )
        usage = LimitService.get_usage(account)
        return Response(usage)


# ─────────────────────────────────────────
#  Admin / Staff endpoints
# ─────────────────────────────────────────

class AdminTransactionListView(ListAPIView):

    serializer_class = TransactionDetailSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        params_serializer = AdminTransactionFilterSerializer(
            data=self.request.query_params
        )
        params_serializer.is_valid(raise_exception=True)
        filters = params_serializer.validated_data

        qs = Transaction.objects.select_related(
            "account__customer"
        ).all()

        if filters.get("account_id"):
            qs = qs.filter(account_id=filters["account_id"])

        if filters.get("type"):
            qs = qs.filter(type=filters["type"])

        if filters.get("status"):
            qs = qs.filter(status=filters["status"])

        if filters.get("date_from"):
            qs = qs.filter(created_at__date__gte=filters["date_from"])

        if filters.get("date_to"):
            qs = qs.filter(created_at__date__lte=filters["date_to"])

        if filters.get("reference_number"):
            qs = qs.filter(
                reference_number__icontains=filters["reference_number"]
            )

        return qs


class AdminTransactionDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        txn = get_object_or_404(
            Transaction.objects.select_related("account__customer"),
            pk=pk,
        )
        return Response(TransactionDetailSerializer(txn).data)


class AdminTransactionByReferenceView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, reference_number):
        txn = get_object_or_404(
            Transaction.objects.select_related("account__customer"),
            reference_number=reference_number,
        )
        return Response(TransactionDetailSerializer(txn).data)


class AdminAccountStatementView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, account_id):
        account = get_object_or_404(Account, id=account_id)
        txns = TransactionService.get_statement(account)
        return Response(TransactionDetailSerializer(txns, many=True).data)


class AdminReverseTransactionView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        serializer = ReverseTransactionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        txn = get_object_or_404(Transaction, pk=pk)

        try:
            refund_txn = TransactionService.reverse_transaction(
                transaction=txn,
                actor=request.user,
            )
        except ValidationError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(TransactionDetailSerializer(refund_txn).data)


class AdminResetLimitView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, account_id):
        account = get_object_or_404(Account, id=account_id)
        LimitService.reset_limits(account)
        return Response({"detail": f"limits reset for account {account_id}"})


class AdminLimitUsageView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, account_id):
        account = get_object_or_404(Account, id=account_id)
        usage = LimitService.get_usage(account)
        return Response(usage)
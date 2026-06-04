from django.shortcuts import get_object_or_404
from django.db.models import Q, Sum, Count
from django.core.exceptions import ValidationError

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from apps.users.models import User

from .models import Account
from .serializers import (
    AccountSerializer,
    AccountDetailSerializer,
    OpenAccountSerializer,
    AdminOpenAccountSerializer,
    AmountSerializer,
    AdminBalanceAdjustSerializer,
    AdminAccountFilterSerializer,
)
from .services import AccountService
from .permissions import IsBankStaff


# ─────────────────────────────────────────
#  Customer endpoints
# ─────────────────────────────────────────

class MyAccountsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = AccountService.my_accounts(request.user)
        return Response(AccountSerializer(qs, many=True).data)


class AccountDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        account = get_object_or_404(Account, pk=pk, customer=request.user)
        return Response(AccountSerializer(account).data)


class OpenAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = OpenAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        account = AccountService.open_account(
            user=request.user,
            bank_id=serializer.validated_data["bank_id"],
            type=serializer.validated_data["type"],
            currency=serializer.validated_data["currency"],
        )
        return Response(
            AccountSerializer(account).data,
            status=status.HTTP_201_CREATED,
        )


class SetPrimaryAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            account = AccountService.set_primary(
                user=request.user,
                account_id=pk,
                actor=request.user,
            )
        except (Account.DoesNotExist, ValidationError) as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(AccountSerializer(account).data)


# ─────────────────────────────────────────
#  Admin / Staff endpoints
# ─────────────────────────────────────────

class AdminAccountListView(ListAPIView):

    serializer_class = AccountDetailSerializer
    permission_classes = [IsAuthenticated, IsBankStaff]

    def get_queryset(self):
        params = AdminAccountFilterSerializer(
            data=self.request.query_params
        )
        params.is_valid(raise_exception=True)
        f = params.validated_data

        qs = Account.objects.select_related(
            "customer", "bank"
        ).all()

        if f.get("customer_id"):
            qs = qs.filter(customer_id=f["customer_id"])
        if f.get("bank_id"):
            qs = qs.filter(bank_id=f["bank_id"])
        if f.get("status"):
            qs = qs.filter(status=f["status"])
        if f.get("type"):
            qs = qs.filter(type=f["type"])
        if f.get("currency"):
            qs = qs.filter(currency=f["currency"])
        if "is_primary" in f:
            qs = qs.filter(is_primary=f["is_primary"])
        if f.get("search"):
            q = f["search"]
            qs = qs.filter(
                Q(account_number__icontains=q) | Q(iban__icontains=q)
            )
        if f.get("date_from"):
            qs = qs.filter(created_at__date__gte=f["date_from"])
        if f.get("date_to"):
            qs = qs.filter(created_at__date__lte=f["date_to"])

        return qs.order_by("-created_at")


class AdminAccountDetailView(APIView):
    permission_classes = [IsAuthenticated, IsBankStaff]

    def get(self, request, pk):
        account = get_object_or_404(
            Account.objects.select_related("customer", "bank"),
            pk=pk,
        )
        return Response(AccountDetailSerializer(account).data)


class AdminAccountByNumberView(APIView):
    permission_classes = [IsAuthenticated, IsBankStaff]

    def get(self, request, account_number):
        account = get_object_or_404(
            Account.objects.select_related("customer", "bank"),
            account_number=account_number,
        )
        return Response(AccountDetailSerializer(account).data)


class AdminAccountByIBANView(APIView):
    permission_classes = [IsAuthenticated, IsBankStaff]

    def get(self, request, iban):
        account = get_object_or_404(
            Account.objects.select_related("customer", "bank"),
            iban=iban,
        )
        return Response(AccountDetailSerializer(account).data)


class AdminCustomerAccountsView(ListAPIView):
    """admin: one special customer accounts list"""
    serializer_class = AccountDetailSerializer
    permission_classes = [IsAuthenticated, IsBankStaff]

    def get_queryset(self):
        get_object_or_404(User, pk=self.kwargs["customer_id"])
        return AccountService.get_customer_accounts(
            self.kwargs["customer_id"]
        )


class AdminOpenAccountView(APIView):
    """admin: open account for one special customer"""
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = AdminOpenAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        customer = get_object_or_404(
            User, pk=serializer.validated_data["customer_id"]
        )

        account = AccountService.open_account(
            user=customer,
            bank_id=serializer.validated_data["bank_id"],
            type=serializer.validated_data["type"],
            currency=serializer.validated_data["currency"],
        )

        if serializer.validated_data.get("is_primary"):
            AccountService.set_primary(
                user=customer,
                account_id=account.id,
                actor=request.user,
            )
            account.refresh_from_db()

        return Response(
            AccountDetailSerializer(account).data,
            status=status.HTTP_201_CREATED,
        )


class AdminSetPrimaryAccountView(APIView):
    """admin: change primary account of pne customer"""
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        account = get_object_or_404(Account, pk=pk)
        try:
            updated = AccountService.set_primary(
                user=account.customer,
                account_id=pk,
                actor=request.user,
            )
        except ValidationError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(AccountDetailSerializer(updated).data)


class DepositView(APIView):
    permission_classes = [IsAuthenticated, IsBankStaff]

    def post(self, request, pk):
        serializer = AmountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            account = AccountService.increase_balance(
                account_id=pk,
                amount=serializer.validated_data["amount"],
                actor=request.user,
            )
        except ValidationError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(AccountDetailSerializer(account).data)


class WithdrawView(APIView):
    permission_classes = [IsAuthenticated, IsBankStaff]

    def post(self, request, pk):
        serializer = AmountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            account = AccountService.withdraw(
                account_id=pk,
                amount=serializer.validated_data["amount"],
                actor=request.user,
            )
        except ValidationError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(AccountDetailSerializer(account).data)


class FreezeView(APIView):
    permission_classes = [IsAuthenticated, IsBankStaff]

    def post(self, request, pk):
        account = AccountService.freeze(pk, actor=request.user)
        return Response(AccountDetailSerializer(account).data)


class ActivateView(APIView):
    permission_classes = [IsAuthenticated, IsBankStaff]

    def post(self, request, pk):
        account = AccountService.activate(pk, actor=request.user)
        return Response(AccountDetailSerializer(account).data)


class CloseView(APIView):
    permission_classes = [IsAuthenticated, IsBankStaff]

    def post(self, request, pk):
        try:
            account = AccountService.close(pk, actor=request.user)
        except ValidationError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(AccountDetailSerializer(account).data)


class BlockBalanceView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        serializer = AdminBalanceAdjustSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            account = AccountService.block_balance(
                account_id=pk,
                amount=serializer.validated_data["amount"],
                actor=request.user,
            )
        except ValidationError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(AccountDetailSerializer(account).data)


class UnblockBalanceView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        serializer = AdminBalanceAdjustSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            account = AccountService.unblock_balance(
                account_id=pk,
                amount=serializer.validated_data["amount"],
                actor=request.user,
            )
        except ValidationError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(AccountDetailSerializer(account).data)


class AdminAccountStatsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = Account.objects.all()

        stats = qs.aggregate(
            total_accounts=Count("id"),
            total_balance=Sum("balance"),
            total_blocked_balance=Sum("blocked_balance"),
            total_loan_blocked=Sum("loan_blocked_balance"),
        )

        by_status = {
            item["status"]: item["count"]
            for item in qs.values("status").annotate(
                count=Count("id")
            )
        }

        by_type = {
            item["type"]: item["count"]
            for item in qs.values("type").annotate(
                count=Count("id")
            )
        }

        by_currency = {
            item["currency"]: item["count"]
            for item in qs.values("currency").annotate(
                count=Count("id")
            )
        }

        return Response({
            **stats,
            "by_status": by_status,
            "by_type": by_type,
            "by_currency": by_currency,
        })
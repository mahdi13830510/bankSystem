# accounts/views.py
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction

from .models import Account, AccountStatus
from .serializers import (
    AccountSerializer,
    AccountCreateSerializer,
    AmountSerializer,
    FreezeUnfreezeSerializer,
    ChangeOwnerSerializer,
    OwnershipHistorySerializer,
    AccountDetailSerializer,
)
from .services import (
    create_account,
    freeze_account,
    unfreeze_account,
    soft_delete_account,
    deposit,
    withdraw,
    block_amount,
    unblock_amount,
    change_account_owner,
)
from .permissions import BankScopePermission, IsAdmin, IsBankStaff
from .exceptions import AccountError, InsufficientBalanceError, InvalidAmountError


# --- Account List and Create ---
class AccountListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin | IsBankStaff]  # Admin/BankStaff can list all accounts

    def get(self, request):
        # Implement filtering logic based on user role if needed
        # For example, BankStaff might only see accounts of their bank
        accounts = Account.objects.filter(status=AccountStatus.ACTIVE)  # Example: only active accounts
        serializer = AccountSerializer(accounts, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = AccountCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            account = create_account(
                customer_id=serializer.validated_data["customer"],
                bank_id=serializer.validated_data["bank"],
                account_type=serializer.validated_data["type"],
                currency=serializer.validated_data["currency"],
                initial_balance=serializer.validated_data.get("balance", 0),
                performed_by=request.user,
            )
            return Response(AccountSerializer(account).data, status=status.HTTP_201_CREATED)
        except AccountError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# --- Account Detail, Update, Soft Delete ---
class AccountDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, BankScopePermission]  # Access limited by BankScopePermission

    def get_object(self, pk):
        # BankScopePermission will check if the user can access this account
        return get_object_or_404(Account, pk=pk)

    def get(self, request, pk):
        account = self.get_object(pk)
        self.check_object_permissions(request, account)
        serializer = AccountDetailSerializer(account)  # Use a more detailed serializer if needed
        return Response(serializer.data)

    def patch(self, request, pk):
        account = self.get_object(pk)
        self.check_object_permissions(request, account)

        serializer = AccountDetailSerializer(account, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Handle updates, e.g., changing type, currency (if allowed)
        # Note: Direct balance updates should ideally go through deposit/withdraw services
        try:
            # Example: updating only allowed fields like description or status if not frozen/deleted
            # For simplicity, let's assume AccountDetailSerializer handles validation
            # and we just save the validated data. More complex logic might be needed.
            updated_account = serializer.save()
            return Response(AccountDetailSerializer(updated_account).data)
        except AccountError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        account = self.get_object(pk)
        self.check_object_permissions(request, account)

        try:
            soft_deleted_account = soft_delete_account(account=account, performed_by=request.user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except AccountError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# --- Account Status Management ---
class FreezeAccountAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin | IsBankStaff]

    def post(self, request, pk):
        account = get_object_or_404(Account, pk=pk)
        self.check_object_permissions(request, account)  # Ensure user has access to this bank's accounts

        serializer = FreezeUnfreezeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            frozen_account = freeze_account(account=account, performed_by=request.user,
                                            reason=serializer.validated_data.get("reason"))
            return Response(AccountSerializer(frozen_account).data)
        except AccountError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UnfreezeAccountAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin | IsBankStaff]

    def post(self, request, pk):
        account = get_object_or_404(Account, pk=pk)
        self.check_object_permissions(request, account)

        serializer = FreezeUnfreezeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            unfrozen_account = unfreeze_account(account=account, performed_by=request.user,
                                                reason=serializer.validated_data.get("reason"))
            return Response(AccountSerializer(unfrozen_account).data)
        except AccountError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# --- Balance Operations (Deposit, Withdraw, Block, Unblock) ---
class DepositAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin | IsBankStaff]

    def post(self, request, pk):
        account = get_object_or_404(Account, pk=pk)
        self.check_object_permissions(request, account)

        serializer = AmountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            # deposit service handles atomic transaction and financial logging
            updated_account, transaction_record = deposit(
                account=account,
                amount=serializer.validated_data["amount"],
                performed_by=request.user,
                reference=request.data.get("reference"),
                description=request.data.get("description", "Deposit"),
            )
            return Response({
                "message": "Deposit successful.",
                "account": AccountSerializer(updated_account).data,
                "transaction_id": transaction_record.id,
            })
        except (AccountError, InvalidAmountError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class WithdrawAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin | IsBankStaff]

    def post(self, request, pk):
        account = get_object_or_404(Account, pk=pk)
        self.check_object_permissions(request, account)

        serializer = AmountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            # withdraw service handles atomic transaction, balance check, and financial logging
            updated_account, transaction_record = withdraw(
                account=account,
                amount=serializer.validated_data["amount"],
                performed_by=request.user,
                reference=request.data.get("reference"),
                description=request.data.get("description", "Withdrawal"),
            )
            return Response({
                "message": "Withdrawal successful.",
                "account": AccountSerializer(updated_account).data,
                "transaction_id": transaction_record.id,
            })
        except (AccountError, InsufficientBalanceError, InvalidAmountError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class BlockAmountAPIView(APIView):
    permission_classes = [IsAuthenticated, BankScopePermission]

    def post(self, request, pk):
        account = get_object_or_404(Account, pk=pk)
        self.check_object_permissions(request, account)

        serializer = AmountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated_account = block_amount(
                account=account,
                amount=serializer.validated_data["amount"],
                performed_by=request.user,
                reason=request.data.get("reason", "Amount blocked"),
            )
            return Response({
                "message": "Amount blocked successfully.",
                "account": AccountSerializer(updated_account).data,
            })
        except (AccountError, InvalidAmountError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UnblockAmountAPIView(APIView):
    permission_classes = [IsAuthenticated, BankScopePermission]

    def post(self, request, pk):
        account = get_object_or_404(Account, pk=pk)
        self.check_object_permissions(request, account)

        serializer = AmountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated_account = unblock_amount(
                account=account,
                amount=serializer.validated_data["amount"],
                performed_by=request.user,
                reason=request.data.get("reason", "Amount unblocked"),
            )
            return Response({
                "message": "Amount unblocked successfully.",
                "account": AccountSerializer(updated_account).data,
            })
        except (AccountError, InvalidAmountError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# --- Account Ownership ---
class ChangeAccountOwnerAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]  # Only Admins can change ownership

    def post(self, request, pk):
        account = get_object_or_404(Account, pk=pk)
        serializer = ChangeOwnerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated_account = change_account_owner(
                account=account,
                new_owner_id=serializer.validated_data["new_owner"],
                performed_by=request.user,
            )
            return Response(AccountSerializer(updated_account).data)
        except AccountError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class OwnershipHistoryListAPIView(APIView):
    permission_classes = [IsAuthenticated, BankScopePermission]  # Access limited by BankScopePermission

    def get(self, request, pk):
        account = get_object_or_404(Account, pk=pk)
        self.check_object_permissions(request, account)

        history = account.ownership_history.all().order_by('-id')  # Assuming related_name is 'ownership_history'
        serializer = OwnershipHistorySerializer(history, many=True)
        return Response(serializer.data)


# --- Customer Specific Views ---
class MyAccountsAPIView(APIView):
    permission_classes = [IsAuthenticated]  # Any logged-in user can see their own accounts

    def get(self, request):
        # Filter accounts by the currently logged-in customer
        # Assuming the user model has a way to identify customer, e.g., 'customer_profile'
        # Or if User directly represents the customer in this context
        try:
            # Adjust this line based on how your User model relates to Customer
            customer_id = request.user.customer_profile.id  # Example if you have a CustomerProfile model
            # Or if User is the customer: customer_id = request.user.id
        except AttributeError:
            return Response({"error": "User profile not found."}, status=status.HTTP_400_BAD_REQUEST)

        accounts = Account.objects.filter(
            customer_id=customer_id,
            status__in=[AccountStatus.ACTIVE, AccountStatus.FROZEN]  # Show active and frozen accounts
        ).order_by('bank__name', 'account_number')

        serializer = AccountSerializer(accounts, many=True)
        return Response(serializer.data)

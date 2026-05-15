# apps/accounts/views.py
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .serializers import (
    AccountSerializer,
    OpenAccountSerializer,
    AmountSerializer
)
from .services import AccountService
from .permissions import IsBankStaff


# -------------------------------
# customer apis
# -------------------------------

class MyAccountsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = AccountService.my_accounts(request.user)
        return Response(AccountSerializer(qs, many=True).data)


class AccountDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        obj = AccountService.get_owned(request.user, pk)
        return Response(AccountSerializer(obj).data)


class OpenAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = OpenAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        account = AccountService.open_account(
            user=request.user,
            bank_id=serializer.validated_data["bank_id"],
            type=serializer.validated_data["type"],
            currency=serializer.validated_data["currency"]
        )

        return Response(AccountSerializer(account).data, status=status.HTTP_201_CREATED)


# -------------------------------
# staff/admin apis
# -------------------------------

class DepositView(APIView):
    permission_classes = [IsAuthenticated, IsBankStaff]

    def post(self, request, pk):
        serializer = AmountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        obj = AccountService.increase_balance(
            pk,
            serializer.validated_data["amount"]
        )
        return Response(AccountSerializer(obj).data)


class FreezeView(APIView):
    permission_classes = [IsAuthenticated, IsBankStaff]

    def post(self, request, pk):
        obj = AccountService.freeze(pk)
        return Response(AccountSerializer(obj).data)


class ActivateView(APIView):
    permission_classes = [IsAuthenticated, IsBankStaff]

    def post(self, request, pk):
        obj = AccountService.activate(pk)
        return Response(AccountSerializer(obj).data)


class CloseView(APIView):
    permission_classes = [IsAuthenticated, IsBankStaff]

    def post(self, request, pk):
        obj = AccountService.close(pk)
        return Response(AccountSerializer(obj).data)
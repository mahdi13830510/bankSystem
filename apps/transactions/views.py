from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.accounts.models import Account

from .services import TransactionService
from .serializers import (
    CardTransferSerializer,
    IbanTransferSerializer,
    TransactionSerializer
)


class CardTransferView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        serializer = CardTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        source = Account.objects.get(
            id=serializer.validated_data["source_account_id"]
        )

        destination = Account.objects.get(
            id=serializer.validated_data["destination_account_id"]
        )

        txn = TransactionService.card_transfer(
            actor=request.user,
            source=source,
            destination=destination,
            amount=serializer.validated_data["amount"],
            ip=request.META.get("REMOTE_ADDR"),
            description=serializer.validated_data.get("description", "")
        )

        return Response(TransactionSerializer(txn).data)


class IbanTransferView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        serializer = IbanTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        source = Account.objects.get(
            id=serializer.validated_data["source_account_id"]
        )

        destination = Account.objects.get(
            iban=serializer.validated_data["destination_iban"]
        )

        txn = TransactionService.iban_transfer(
            actor=request.user,
            source=source,
            destination=destination,
            amount=serializer.validated_data["amount"],
            ip=request.META.get("REMOTE_ADDR")
        )

        return Response(TransactionSerializer(txn).data)


class StatementView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, account_id):

        account = Account.objects.get(id=account_id)

        txns = TransactionService.get_statement(account)

        return Response(
            TransactionSerializer(txns, many=True).data
        )
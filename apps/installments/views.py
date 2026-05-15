from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Installment
from .serializers import InstallmentSerializer
from .services import InstallmentService


class MyInstallmentsView(ListAPIView):
    serializer_class = InstallmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Installment.objects.filter(
            loan__customer=self.request.user
        )


class PayInstallmentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):

        installment = Installment.objects.get(pk=pk)

        InstallmentService.pay_installment(
            request.user,
            installment
        )

        return Response({"detail": "paid"})


class RemainingDebtView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, loan_id):

        loan = request.user.loan_set.get(pk=loan_id)

        debt = InstallmentService.remaining_debt(loan)

        return Response({"remaining_debt": debt})
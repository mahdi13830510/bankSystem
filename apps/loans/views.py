from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import *
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from .serializers import *
from .services import LoanService


class LoanRequestCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        serializer = LoanRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        req = LoanService.create_request(
            request.user,
            serializer.validated_data
        )

        return Response({"id": req.id})


class MyLoanRequestsView(ListAPIView):
    serializer_class = LoanRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return LoanRequest.objects.filter(customer=self.request.user)


class AdminPendingLoansView(ListAPIView):
    serializer_class = LoanRequestSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return LoanRequest.objects.filter(status="UNDER_REVIEW")


class ApproveLoanView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):

        req = LoanRequest.objects.get(pk=pk)

        loan = LoanService.approve_request(
            request.user,
            req
        )

        return Response({"loan_id": loan.id})


class RejectLoanView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):

        req = LoanRequest.objects.get(pk=pk)

        LoanService.reject_request(
            request.user,
            req,
            request.data["reason"]
        )

        return Response({"detail": "rejected"})


class MyLoansView(ListAPIView):
    serializer_class = LoanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Loan.objects.filter(customer=self.request.user)
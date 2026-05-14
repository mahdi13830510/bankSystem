from rest_framework.generics import (
    ListAPIView,
    RetrieveAPIView,
    CreateAPIView,
    UpdateAPIView
)
from rest_framework.permissions import IsAdminUser

from .models import Bank, Branch
from .serializers import (
    BankSerializer,
    BranchSerializer
)


class BankListView(ListAPIView):
    queryset = Bank.objects.filter(status="ACTIVE")
    serializer_class = BankSerializer


class BankDetailView(RetrieveAPIView):
    queryset = Bank.objects.all()
    serializer_class = BankSerializer


class BankCreateView(CreateAPIView):
    queryset = Bank.objects.all()
    serializer_class = BankSerializer
    permission_classes = [IsAdminUser]


class BankStatusUpdateView(UpdateAPIView):
    queryset = Bank.objects.all()
    serializer_class = BankSerializer
    permission_classes = [IsAdminUser]


class BranchListView(ListAPIView):
    serializer_class = BranchSerializer

    def get_queryset(self):
        return Branch.objects.filter(
            bank_id=self.kwargs["bank_id"],
            is_active=True
        )
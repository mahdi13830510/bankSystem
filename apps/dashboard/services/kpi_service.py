from django.db.models import Sum, Avg

from apps.accounts.models import Account
from apps.transactions.models import Transaction
from apps.loans.models import Loan
from apps.users.models import User


class KPIService:

    @staticmethod
    def financial():

        return {
            "total_balance": Account.objects.aggregate(Sum("balance"))["balance__sum"] or 0,
            "avg_balance": Account.objects.aggregate(Avg("balance"))["balance__avg"] or 0,
        }

    @staticmethod
    def users():
        return {
            "total_users": User.objects.count(),
            "active_users": User.objects.filter(is_active=True).count(),
        }

    @staticmethod
    def loans():
        return {
            "active_loans": Loan.objects.filter(status="ACTIVE").count(),
            "pending_loans": Loan.objects.filter(status="PENDING").count(),
        }

    @staticmethod
    def transactions():
        return {
            "total": Transaction.objects.count(),
        }
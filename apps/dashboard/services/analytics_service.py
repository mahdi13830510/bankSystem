from django.db.models import Sum
from django.utils.timezone import now, timedelta

from apps.transactions.models import Transaction


class AnalyticsService:

    @staticmethod
    def daily_trend(days=7):

        result = []

        for i in range(days):

            day = now().date() - timedelta(days=i)

            total = Transaction.objects.filter(
                created_at__date=day
            ).aggregate(Sum("amount"))["amount__sum"] or 0

            result.append({
                "date": str(day),
                "volume": total
            })

        return list(reversed(result))
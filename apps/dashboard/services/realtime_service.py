from django.utils.timezone import now

from apps.transactions.models import Transaction


class RealtimeService:

    @staticmethod
    def live():

        return {
            "tx_last_minute": Transaction.objects.filter(
                created_at__gte=now()
            ).count(),

            "system_status": "HEALTHY"
        }
from apps.fraud.models import FraudReport


class FraudDashboardService:

    @staticmethod
    def fraud_summary():

        return {
            "total_alerts": FraudReport.objects.count(),
            "high_risk": FraudReport.objects.filter(risk_score__gte=80).count(),
            "medium_risk": FraudReport.objects.filter(risk_score__range=(50, 79)).count(),
            "resolved": FraudReport.objects.filter(is_resolved=True).count(),
        }

    @staticmethod
    def recent_alerts(limit=10):

        return list(
            FraudAlert.objects.order_by("-created_at")[:limit].values()
        )
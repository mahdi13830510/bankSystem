from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from .services.kpi_service import KPIService
from .services.analytics_service import AnalyticsService
from .services.fraud_service import FraudDashboardService
from .services.realtime_service import RealtimeService


class DashboardView(APIView):

    permission_classes = [IsAdminUser]

    def get(self, request):

        return Response({
            "kpis": {
                "financial": KPIService.financial(),
                "users": KPIService.users(),
                "loans": KPIService.loans(),
                "transactions": KPIService.transactions(),
            },

            "analytics": {
                "trend": AnalyticsService.daily_trend(),
            },

            "fraud": FraudDashboardService.fraud_summary(),
            "recent_fraud_alerts": FraudDashboardService.recent_alerts(),

            "realtime": RealtimeService.live(),
        })
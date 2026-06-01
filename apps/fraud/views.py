from rest_framework.views import APIView
from rest_framework.response import Response

from .models import FraudReport


class FraudReportListView(APIView):

    def get(self, request):
        reports = FraudReport.objects.order_by("-created_at", "-pk")
        return Response([
            {
                "id": r.id,
                "score": r.score,
                "decision": r.decision,
                "transaction_id": r.transaction_id
            }
            for r in reports
        ])

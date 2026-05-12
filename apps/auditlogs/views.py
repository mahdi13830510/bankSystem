from rest_framework.views import APIView
from rest_framework.response import Response
from .models import AuditLog


class AuditLogListView(APIView):

    def get(self, request):

        logs = AuditLog.objects.all()[:100]

        return Response([
            {
                "action": l.action,
                "entity_type": l.entity_type,
                "entity_id": l.entity_id,
                "created_at": l.created_at
            }
            for l in logs
        ])
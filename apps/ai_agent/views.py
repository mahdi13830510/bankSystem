# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .serializers import ChatSerializer
from .services.conversation_service import ConversationService


class ChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        text = serializer.validated_data["message"]
        conversation_id = serializer.validated_data.get("conversation_id")

        result = ConversationService.process_message(
            user=request.user,
            text=text,
            ip_address=request.META.get("REMOTE_ADDR"),
            conversation_id=conversation_id,
        )

        return Response(result, status=status.HTTP_200_OK)



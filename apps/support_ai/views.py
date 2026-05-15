from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .services import AIService
from .models import AIConversation
from .serializers import AIConversationSerializer


class ChatWithAIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        message = request.data.get("message")

        response = AIService.send_message(
            request.user,
            message
        )

        return Response({"response": response})


class ConversationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        conv = AIConversation.objects.filter(user=request.user).first()

        return Response(
            AIConversationSerializer(conv).data
        )
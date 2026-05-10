from rest_framework.views import APIView
from rest_framework.response import Response

from .serializers import RegisterSerializer
from .services import UserService


class RegisterView(APIView):

    def post(self, request):

        serializer = RegisterSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        user = UserService.register_user(
            serializer.validated_data
        )

        return Response({
            "message": "registered",
            "user_id": user.id
        })
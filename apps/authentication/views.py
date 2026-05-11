from rest_framework.views import APIView
from rest_framework.response import Response

from .serializers import (
    LoginSerializer,
    VerifyOTPSerializer,
    RefreshSerializer
)

from .services import AuthService


class LoginView(APIView):

    def post(self, request):

        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = AuthService.login(
            serializer.validated_data["phone"],
            serializer.validated_data["password"],
            request.META.get("REMOTE_ADDR"),
            request.META.get("HTTP_USER_AGENT")
        )

        return Response({
            "message": "OTP sent"
        })


class VerifyOTPView(APIView):

    def post(self, request):

        serializer = VerifyOTPSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        access, refresh = AuthService.verify_otp(
            serializer.validated_data["phone"],
            serializer.validated_data["code"],
            request.META.get("REMOTE_ADDR"),
            request.META.get("HTTP_USER_AGENT")
        )

        return Response({
            "access_token": access,
            "refresh_token": refresh
        })


class LogoutView(APIView):

    def post(self, request):

        token = request.data["refresh_token"]

        AuthService.logout(token)

        return Response({"message": "logged out"})
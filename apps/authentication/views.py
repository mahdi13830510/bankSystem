from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import status

from apps.users.models import User

from .models import Session, OTPCode
from .serializers import (
    LoginSerializer,
    VerifyOTPSerializer,
    RefreshSerializer,
    SessionSerializer,
    SessionListSerializer,
    OTPCodeSerializer,
    AdminSessionFilterSerializer,
)
from .services import AuthService


# ─────────────────────────────────────────
#  Public — Auth flow
# ─────────────────────────────────────────

class LoginView(APIView):
    """step one: send password and و receive OTP"""

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        AuthService.login(
            phone=serializer.validated_data["phone"],
            password=serializer.validated_data["password"],
            ip=request.META.get("REMOTE_ADDR"),
            device=request.META.get("HTTP_USER_AGENT"),
        )

        return Response({"message": "OTP sent"})


class VerifyOTPView(APIView):
    """step two: confirm OTP and receive token"""

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        access, refresh = AuthService.verify_otp(
            phone=serializer.validated_data["phone"],
            code=serializer.validated_data["code"],
            ip=request.META.get("REMOTE_ADDR", "127.0.0.1"),
            device=request.META.get("HTTP_USER_AGENT", "Unknown Device"),
        )

        return Response({
            "access_token": access,
            "refresh_token": refresh,
        })


class RefreshTokenView(APIView):

    def post(self, request):
        serializer = RefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_access = AuthService.refresh_token(
            serializer.validated_data["refresh_token"]
        )

        return Response({"access_token": new_access})


class LogoutView(APIView):
    """logout — revoke  session"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh_token")
        if not refresh_token:
            return Response(
                {"detail": "refresh_token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        AuthService.logout(
            refresh_token_str=refresh_token,
            actor=request.user,
        )
        return Response({"message": "logged out"})


# ─────────────────────────────────────────
#  Customer
# ─────────────────────────────────────────

class MySessionsView(ListAPIView):
    serializer_class = SessionListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Session.objects.filter(
            user=self.request.user,
            status=Session.Status.ACTIVE,
        ).order_by("-last_used")


class RevokeMySessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        session = get_object_or_404(
            Session,
            pk=pk,
            user=request.user,
        )
        AuthService.revoke_session(session, actor=request.user)
        return Response({"detail": "session revoked"})


class RevokeOtherSessionsView(APIView):
    """
User: revoke all other sessions.
The current session (identified by the provided refresh token) remains active.
"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh_token")

        current_session = None
        if refresh_token:
            current_session = Session.objects.filter(
                refresh_token=refresh_token,
                user=request.user,
            ).first()

        count = AuthService.revoke_all_sessions(
            user=request.user,
            exclude_session_id=current_session.id if current_session else None,
            actor=request.user,
        )
        return Response({
            "detail": f"{count} session(s) revoked"
        })


# ─────────────────────────────────────────
#  Admin — Sessions
# ─────────────────────────────────────────

class AdminSessionListView(ListAPIView):
    """
    filter: user_id,status,ip_address,date_from,date_to
    """
    serializer_class = SessionSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        params = AdminSessionFilterSerializer(
            data=self.request.query_params
        )
        params.is_valid(raise_exception=True)
        f = params.validated_data

        qs = Session.objects.select_related("user").all()

        if f.get("user_id"):
            qs = qs.filter(user_id=f["user_id"])
        if f.get("status"):
            qs = qs.filter(status=f["status"])
        if f.get("ip_address"):
            qs = qs.filter(ip_address=f["ip_address"])
        if f.get("date_from"):
            qs = qs.filter(created_at__date__gte=f["date_from"])
        if f.get("date_to"):
            qs = qs.filter(created_at__date__lte=f["date_to"])

        return qs.order_by("-created_at")


class AdminSessionDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        session = get_object_or_404(
            Session.objects.select_related("user"), pk=pk
        )
        return Response(SessionSerializer(session).data)


class AdminRevokeSessionView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        session = get_object_or_404(Session, pk=pk)
        AuthService.revoke_session(session, actor=request.user)
        return Response({"detail": "session revoked"})


class AdminUserSessionsView(ListAPIView):
    serializer_class = SessionSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return Session.objects.filter(
            user_id=self.kwargs["user_id"]
        ).select_related("user").order_by("-created_at")


class AdminRevokeAllUserSessionsView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        count = AuthService.revoke_all_sessions(
            user=user,
            actor=request.user,
        )
        return Response({
            "detail": f"{count} session(s) revoked for user {user_id}"
        })


# ─────────────────────────────────────────
#  Admin — OTP
# ─────────────────────────────────────────

class AdminUserOTPListView(ListAPIView):
    """Admin: list of a user's OTPs (for audit purposes)"""
    serializer_class = OTPCodeSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return OTPCode.objects.filter(
            user_id=self.kwargs["user_id"]
        ).order_by("-created_at")


class AdminInvalidateUserOTPsView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        count = AuthService.invalidate_user_otps(
            user=user,
            actor=request.user,
        )
        return Response({
            "detail": f"{count} OTP(s) invalidated for user {user_id}"
        })
from django.shortcuts import get_object_or_404
from django.db.models import Q

from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import status

from .models import User, UserDevice
from .serializers import (
    RegisterSerializer,
    MeSerializer,
    UserListSerializer,
    UserDetailSerializer,
    ChangePasswordSerializer,
    AdminUserUpdateSerializer,
    BlockUserSerializer,
    ChangeRoleSerializer,
    ProfileSerializer,
    ProfileUpdateSerializer,
    UserDeviceSerializer,
    AdminUserFilterSerializer,
)
from .services import UserService


# ─────────────────────────────────────────
#  Public
# ─────────────────────────────────────────

class RegisterView(APIView):
    """new user register"""

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = UserService.register_user(serializer.validated_data)
        return Response(
            {"message": "registered", "user_id": user.id},
            status=status.HTTP_201_CREATED,
        )


# ─────────────────────────────────────────
#  Customer
# ─────────────────────────────────────────

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(MeSerializer(request.user).data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.check_password(serializer.validated_data["old_password"]):
            return Response(
                {"old_password": "Wrong password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        UserService.change_password(
            user=user,
            new_password=serializer.validated_data["new_password"],
        )
        return Response({"detail": "password changed"})


class MyProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = UserService.get_or_create_profile(request.user)
        return Response(ProfileSerializer(profile).data)

    def patch(self, request):
        serializer = ProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = UserService.update_profile(
            user=request.user,
            data=serializer.validated_data,
        )
        return Response(ProfileSerializer(profile).data)


class MyDevicesView(ListAPIView):
    serializer_class = UserDeviceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserDevice.objects.filter(user=self.request.user)


class DeleteMyDeviceView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        device = get_object_or_404(
            UserDevice, pk=pk, user=request.user
        )
        device.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────
#  Admin / Staff
# ─────────────────────────────────────────

class AdminUserListView(ListAPIView):
    """
    filter: status,primary_role,is_verified=,search,&date_from,date_to
    """
    serializer_class = UserListSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        params = AdminUserFilterSerializer(data=self.request.query_params)
        params.is_valid(raise_exception=True)
        f = params.validated_data

        qs = User.objects.all()

        if f.get("status"):
            qs = qs.filter(status=f["status"])
        if f.get("primary_role"):
            qs = qs.filter(primary_role=f["primary_role"])
        if "is_verified" in f:
            qs = qs.filter(is_verified=f["is_verified"])
        if f.get("search"):
            q = f["search"]
            qs = qs.filter(
                Q(fullname__icontains=q)
                | Q(phone__icontains=q)
                | Q(email__icontains=q)
                | Q(national_code__icontains=q)
            )
        if f.get("date_from"):
            qs = qs.filter(date_joined__date__gte=f["date_from"])
        if f.get("date_to"):
            qs = qs.filter(date_joined__date__lte=f["date_to"])

        return qs.order_by("-date_joined")


class AdminUserDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        return Response(UserDetailSerializer(user).data)

    def patch(self, request, pk):
        """ change status / role / is_staff"""
        user = get_object_or_404(User, pk=pk)
        serializer = AdminUserUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        for field, value in serializer.validated_data.items():
            setattr(user, field, value)
        user.save()

        return Response(UserDetailSerializer(user).data)


class AdminVerifyUserView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        UserService.verify_user(user, actor=request.user)
        return Response({"detail": "user verified"})


class AdminBlockUserView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        serializer = BlockUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        UserService.block_user(
            user=user,
            actor=request.user,
            blocked_until=serializer.validated_data.get("blocked_until"),
            reason=serializer.validated_data.get("reason", ""),
        )
        return Response({"detail": "user blocked"})


class AdminUnblockUserView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        UserService.unblock_user(user, actor=request.user)
        return Response({"detail": "user unblocked"})


class AdminSuspendUserView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        reason = request.data.get("reason", "")
        UserService.suspend_user(user, actor=request.user, reason=reason)
        return Response({"detail": "user suspended"})


class AdminActivateUserView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        UserService.activate_user(user, actor=request.user)
        return Response({"detail": "user activated"})


class AdminChangeRoleView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        serializer = ChangeRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        UserService.change_role(
            user=user,
            new_role=serializer.validated_data["primary_role"],
            actor=request.user,
        )
        return Response({"detail": "role changed", "primary_role": user.primary_role})


class AdminResetFailedAttemptsView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        UserService.reset_failed_attempts(user, actor=request.user)
        return Response({"detail": "failed attempts reset"})


class AdminResetPasswordView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        new_password = request.data.get("new_password")
        if not new_password or len(new_password) < 8:
            return Response(
                {"detail": "new_password must be at least 8 characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        UserService.change_password(
            user=user,
            new_password=new_password,
            actor=request.user,
        )
        return Response({"detail": "password reset"})


class AdminUserProfileView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        profile = UserService.get_or_create_profile(user)
        return Response(ProfileSerializer(profile).data)

    def patch(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        serializer = ProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = UserService.update_profile(
            user=user,
            data=serializer.validated_data,
            actor=request.user,
        )
        return Response(ProfileSerializer(profile).data)


class AdminUserDevicesView(ListAPIView):
    serializer_class = UserDeviceSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return UserDevice.objects.filter(
            user_id=self.kwargs["pk"]
        )


class AdminDeleteDeviceView(APIView):
    permission_classes = [IsAdminUser]

    def delete(self, request, pk, device_pk):
        device = get_object_or_404(
            UserDevice, pk=device_pk, user_id=pk
        )
        device.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
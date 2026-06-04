from django.shortcuts import get_object_or_404

from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from apps.users.models import User

from .models import Notification
from .serializers import (
    NotificationSerializer,
    SendNotificationSerializer,
    BroadcastSerializer,
)
from .services import NotificationService


# ─────────────────────────────────────────
#  Customer endpoints
# ─────────────────────────────────────────

class MyNotificationsView(ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class MarkAsReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        obj = get_object_or_404(Notification, pk=pk, user=request.user)
        NotificationService.mark_read(obj)
        return Response({"detail": "read"})


class MarkAllAsReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        unread = NotificationService.get_unread(request.user)
        for n in unread:
            NotificationService.mark_read(n)
        return Response({"detail": "all marked as read"})


class UnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        return Response({"unread": count})


# ─────────────────────────────────────────
#  Admin / Staff endpoints
# ─────────────────────────────────────────

class AdminNotificationListView(ListAPIView):
    # can be filtered by status, channel , user id

    serializer_class = NotificationSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        qs = Notification.objects.all()

        user_id = self.request.query_params.get("user_id")
        status = self.request.query_params.get("status")
        channel = self.request.query_params.get("channel")

        if user_id:
            qs = qs.filter(user_id=user_id)
        if status:
            qs = qs.filter(status=status)
        if channel:
            qs = qs.filter(channel=channel)

        return qs


class AdminUserNotificationsView(ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return Notification.objects.filter(
            user_id=self.kwargs["user_id"]
        )


class AdminSendNotificationView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = SendNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        user = get_object_or_404(User, pk=data["user_id"])

        obj = NotificationService.send(
            user=user,
            title=data["title"],
            message=data["message"],
            channel=data.get("channel", "IN_APP"),
            metadata=data.get("metadata", {}),
        )

        return Response(
            NotificationSerializer(obj).data,
            status=status.HTTP_201_CREATED
        )


class AdminBroadcastView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = BroadcastSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        users = User.objects.filter(status="active")

        NotificationService.broadcast(
            users=users,
            title=data["title"],
            message=data["message"],
        )

        return Response(
            {"detail": f"broadcast sent to {users.count()} users"}
        )


class AdminDeleteNotificationView(APIView):
    permission_classes = [IsAdminUser]

    def delete(self, request, pk):
        obj = get_object_or_404(Notification, pk=pk)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

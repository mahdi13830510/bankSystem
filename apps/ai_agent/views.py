from django.shortcuts import get_object_or_404
from django.db.models import Q, Count

from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import status

from .models import AgentConversation, AgentMessage, PendingAction
from .serializers import (
    ChatSerializer,
    AgentMessageSerializer,
    ConversationListSerializer,
    ConversationDetailSerializer,
    AdminConversationSerializer,
    PendingActionSerializer,
    AdminPendingActionSerializer,
    AdminConversationFilterSerializer,
    AdminPendingActionFilterSerializer,
)
from .services.conversation_service import ConversationService


# ─────────────────────────────────────────
#  Customer — Chat
# ─────────────────────────────────────────

class ChatView(APIView):
    """user: send message to AI agent"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = ConversationService.process_message(
                user=request.user,
                text=serializer.validated_data["message"],
                ip_address=request.META.get("REMOTE_ADDR"),
                conversation_id=serializer.validated_data.get("conversation_id"),
            )
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(result, status=status.HTTP_200_OK)


# ─────────────────────────────────────────
#  Customer — Conversations
# ─────────────────────────────────────────

class MyConversationsView(ListAPIView):
    """user: own conversation list"""
    serializer_class = ConversationListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AgentConversation.objects.filter(
            user=self.request.user
        ).prefetch_related("messages").order_by("-updated_at")


class MyConversationDetailView(APIView):
    """user: conversation detail"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        conv = get_object_or_404(
            AgentConversation, pk=pk, user=request.user
        )
        return Response(ConversationDetailSerializer(conv).data)

    def delete(self, request, pk):
        conv = get_object_or_404(
            AgentConversation, pk=pk, user=request.user
        )
        conv.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyConversationMessagesView(ListAPIView):
    """user: message list of one special conversation (paginated)"""
    serializer_class = AgentMessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        get_object_or_404(
            AgentConversation,
            pk=self.kwargs["pk"],
            user=self.request.user,
        )
        return AgentMessage.objects.filter(
            conversation_id=self.kwargs["pk"]
        ).order_by("created_at")


# ─────────────────────────────────────────
#  Customer — Pending Actions
# ─────────────────────────────────────────

class MyPendingActionsView(ListAPIView):
    serializer_class = PendingActionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PendingAction.objects.filter(
            user=self.request.user,
            status=PendingAction.Status.PENDING,
        ).order_by("-created_at")


class CancelPendingActionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        action = get_object_or_404(
            PendingAction,
            pk=pk,
            user=request.user,
            status=PendingAction.Status.PENDING,
        )
        action.status = PendingAction.Status.CANCELLED
        action.save(update_fields=["status"])
        return Response({"detail": "action cancelled"})


# ─────────────────────────────────────────
#  Admin — Conversations
# ─────────────────────────────────────────

class AdminConversationListView(ListAPIView):
    """
    admin: conversation list
    filter: ?user_id=&date_from=&date_to=&search=
    """
    serializer_class = AdminConversationSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        params = AdminConversationFilterSerializer(
            data=self.request.query_params
        )
        params.is_valid(raise_exception=True)
        f = params.validated_data

        qs = AgentConversation.objects.select_related(
            "user"
        ).prefetch_related("messages").all()

        if f.get("user_id"):
            qs = qs.filter(user_id=f["user_id"])
        if f.get("date_from"):
            qs = qs.filter(created_at__date__gte=f["date_from"])
        if f.get("date_to"):
            qs = qs.filter(created_at__date__lte=f["date_to"])
        if f.get("search"):
            qs = qs.filter(
                messages__content__icontains=f["search"]
            ).distinct()

        return qs.order_by("-created_at")


class AdminConversationDetailView(APIView):
    """admin: one conversation detail"""
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        conv = get_object_or_404(
            AgentConversation.objects.select_related("user")
            .prefetch_related("messages"),
            pk=pk,
        )
        return Response(AdminConversationSerializer(conv).data)

    def delete(self, request, pk):
        conv = get_object_or_404(AgentConversation, pk=pk)
        conv.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminUserConversationsView(ListAPIView):
    """admin: one special user conversations"""
    serializer_class = AdminConversationSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return AgentConversation.objects.filter(
            user_id=self.kwargs["user_id"]
        ).select_related("user").prefetch_related("messages").order_by("-created_at")


# ─────────────────────────────────────────
#  Admin — Pending Actions
# ─────────────────────────────────────────

class AdminPendingActionListView(ListAPIView):
    """
    admin: pending actions list
    filter: ?user_id=&intent=&status=&date_from=&date_to=
    """
    serializer_class = AdminPendingActionSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        params = AdminPendingActionFilterSerializer(
            data=self.request.query_params
        )
        params.is_valid(raise_exception=True)
        f = params.validated_data

        qs = PendingAction.objects.select_related("user").all()

        if f.get("user_id"):
            qs = qs.filter(user_id=f["user_id"])
        if f.get("intent"):
            qs = qs.filter(intent=f["intent"])
        if f.get("status"):
            qs = qs.filter(status=f["status"])
        if f.get("date_from"):
            qs = qs.filter(created_at__date__gte=f["date_from"])
        if f.get("date_to"):
            qs = qs.filter(created_at__date__lte=f["date_to"])

        return qs.order_by("-created_at")


class AdminPendingActionDetailView(APIView):
    """admin:  pending action detail"""
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        action = get_object_or_404(
            PendingAction.objects.select_related("user"), pk=pk
        )
        return Response(AdminPendingActionSerializer(action).data)


class AdminCancelPendingActionView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        action = get_object_or_404(
            PendingAction,
            pk=pk,
            status=PendingAction.Status.PENDING,
        )
        action.status = PendingAction.Status.CANCELLED
        action.save(update_fields=["status"])
        return Response({"detail": "action cancelled by admin"})


# ─────────────────────────────────────────
#  Admin — Stats
# ─────────────────────────────────────────

class AdminAgentStatsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        total_conversations = AgentConversation.objects.count()
        total_messages = AgentMessage.objects.count()
        total_actions = PendingAction.objects.count()

        actions_by_status = {
            item["status"]: item["count"]
            for item in PendingAction.objects.values("status").annotate(
                count=Count("id")
            )
        }

        actions_by_intent = {
            item["intent"]: item["count"]
            for item in PendingAction.objects.values("intent").annotate(
                count=Count("id")
            ).order_by("-count")
        }

        return Response({
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "total_actions": total_actions,
            "actions_by_status": actions_by_status,
            "actions_by_intent": actions_by_intent,
        })

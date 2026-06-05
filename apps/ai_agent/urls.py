from django.urls import path
from .views import (
    # customer — chat
    ChatView,
    # customer — conversations
    MyConversationsView,
    MyConversationDetailView,
    MyConversationMessagesView,
    # customer — pending actions
    MyPendingActionsView,
    CancelPendingActionView,
    # admin — conversations
    AdminConversationListView,
    AdminConversationDetailView,
    AdminUserConversationsView,
    # admin — pending actions
    AdminPendingActionListView,
    AdminPendingActionDetailView,
    AdminCancelPendingActionView,
    # admin — stats
    AdminAgentStatsView,
)

urlpatterns = [
    # ── Customer: chat ─────────────────────────────────────────────
    path("chat/",                               ChatView.as_view()),

    # ── Customer: conversations ────────────────────────────────────
    path("conversations/",                      MyConversationsView.as_view()),
    path("conversations/<int:pk>/",             MyConversationDetailView.as_view()),
    path("conversations/<int:pk>/messages/",    MyConversationMessagesView.as_view()),

    # ── Customer: pending actions ──────────────────────────────────
    path("actions/pending/",                    MyPendingActionsView.as_view()),
    path("actions/<int:pk>/cancel/",            CancelPendingActionView.as_view()),

    # ── Admin: conversations ───────────────────────────────────────
    path("admin/conversations/",                        AdminConversationListView.as_view()),
    path("admin/conversations/<int:pk>/",               AdminConversationDetailView.as_view()),
    path("admin/users/<int:user_id>/conversations/",    AdminUserConversationsView.as_view()),

    # ── Admin: pending actions ─────────────────────────────────────
    path("admin/actions/",                      AdminPendingActionListView.as_view()),
    path("admin/actions/<int:pk>/",             AdminPendingActionDetailView.as_view()),
    path("admin/actions/<int:pk>/cancel/",      AdminCancelPendingActionView.as_view()),

    # ── Admin: stats ───────────────────────────────────────────────
    path("admin/stats/",                        AdminAgentStatsView.as_view()),
]
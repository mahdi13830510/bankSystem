import json

from django.contrib import admin, messages
from django.db.models import Count, Q
from django.shortcuts import render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import Notification, NotificationChannel, NotificationStatus
from .services import NotificationService

# ---------------------------------------------------------------------------
# Badge helpers
# ---------------------------------------------------------------------------

STATUS_COLORS = {
    "PENDING": "#fd7e14",
    "SENT":    "#417690",
    "FAILED":  "#dc3545",
    "READ":    "#28a745",
}

CHANNEL_COLORS = {
    "IN_APP": "#417690",
    "SMS":    "#6f42c1",
    "EMAIL":  "#17a2b8",
    "PUSH":   "#fd7e14",
}

CHANNEL_ICONS = {
    "IN_APP": "&#128274;",
    "SMS":    "&#128241;",
    "EMAIL":  "&#9993;",
    "PUSH":   "&#128276;",
}


def _status_badge(status):
    color = STATUS_COLORS.get(status, "#999")
    return format_html(
        '<span style="background:{};color:#fff;padding:2px 10px;border-radius:12px;'
        'font-size:11px;font-weight:600;letter-spacing:.5px">{}</span>',
        color,
        status,
    )


def _channel_badge(channel):
    color = CHANNEL_COLORS.get(channel, "#999")
    icon  = CHANNEL_ICONS.get(channel, "")
    return format_html(
        '<span style="background:{};color:#fff;padding:2px 10px;border-radius:12px;'
        'font-size:11px;font-weight:600;letter-spacing:.5px">{} {}</span>',
        color,
        mark_safe(icon),
        channel,
    )


def _bool_icon(value):
    if value:
        return mark_safe(
            '<span style="color:#28a745;font-size:16px;font-weight:bold">&#10004;</span>'
        )
    return mark_safe(
        '<span style="color:#dc3545;font-size:16px;font-weight:bold">&#10008;</span>'
    )


# ---------------------------------------------------------------------------
# Bulk actions
# ---------------------------------------------------------------------------

@admin.action(description="Mark selected notifications as READ")
def mark_as_read(modeladmin, request, queryset):
    updated = 0
    for notif in queryset.filter(is_read=False):
        NotificationService.mark_read(notif)
        updated += 1
    messages.success(request, f"{updated} notification(s) marked as read.")


@admin.action(description="Mark selected notifications as FAILED")
def mark_as_failed(modeladmin, request, queryset):
    updated = queryset.update(status=NotificationStatus.FAILED)
    messages.warning(request, f"{updated} notification(s) marked as FAILED.")


@admin.action(description="Resend selected notifications (set back to SENT)")
def resend_notifications(modeladmin, request, queryset):
    updated = queryset.update(
        status=NotificationStatus.SENT,
        sent_at=timezone.now(),
    )
    messages.success(request, f"{updated} notification(s) re-queued as SENT.")


# ---------------------------------------------------------------------------
# NotificationAdmin
# ---------------------------------------------------------------------------

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    change_list_template = "admin/notifications/notification_changelist.html"

    # ------------------------------------------------------------------
    # List view
    # ------------------------------------------------------------------
    list_display = (
        "short_id", "user_link", "title_short",
        "channel_display", "status_display",
        "read_icon", "sent_at", "created_at",
    )
    list_filter = (
        "status",
        "channel",
        "is_read",
        ("created_at", admin.DateFieldListFilter),
    )
    search_fields = (
        "title", "message",
        "user__fullname", "user__phone",
    )
    ordering      = ("-created_at",)
    list_per_page = 50
    date_hierarchy = "created_at"
    actions        = [mark_as_read, mark_as_failed, resend_notifications]

    # ------------------------------------------------------------------
    # Detail view
    # ------------------------------------------------------------------
    readonly_fields = (
        "id", "user", "created_at", "sent_at", "read_at",
        "status_badge_detail", "channel_badge_detail",
        "read_icon", "metadata_pretty",
    )

    fieldsets = (
        ("Identity", {
            "fields": ("id", "user", "created_at"),
        }),
        ("Content", {
            "fields": ("title", "message"),
        }),
        ("Delivery", {
            "fields": (
                "channel", "channel_badge_detail",
                "status", "status_badge_detail",
                "sent_at",
            ),
        }),
        ("Read State", {
            "fields": ("is_read", "read_icon", "read_at"),
        }),
        ("Metadata", {
            "fields": ("metadata_pretty",),
            "classes": ("collapse",),
        }),
    )

    # Notifications are system-generated — no manual creation allowed
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    # ------------------------------------------------------------------
    # Extra admin views
    # ------------------------------------------------------------------

    def get_urls(self):
        urls = super().get_urls()
        extra = [
            path(
                "dashboard/",
                self.admin_site.admin_view(self.dashboard_view),
                name="notifications_notification_dashboard",
            ),
            path(
                "broadcast/",
                self.admin_site.admin_view(self.broadcast_view),
                name="notifications_notification_broadcast",
            ),
        ]
        return extra + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        qs      = Notification.objects.all()
        total   = qs.count()
        pending = qs.filter(status=NotificationStatus.PENDING).count()
        sent    = qs.filter(status=NotificationStatus.SENT).count()
        failed  = qs.filter(status=NotificationStatus.FAILED).count()
        read    = qs.filter(status=NotificationStatus.READ).count()
        unread  = qs.filter(is_read=False).count()

        extra_context["summary_cards"] = [
            {"label": "Total",   "value": total,   "color": "#333"},
            {"label": "Pending", "value": pending, "color": "#fd7e14"},
            {"label": "Sent",    "value": sent,    "color": "#417690"},
            {"label": "Failed",  "value": failed,  "color": "#dc3545"},
            {"label": "Read",    "value": read,    "color": "#28a745"},
            {"label": "Unread",  "value": unread,  "color": "#6f42c1"},
        ]
        extra_context["dashboard_url"]  = reverse("admin:notifications_notification_dashboard")
        extra_context["broadcast_url"]  = reverse("admin:notifications_notification_broadcast")
        return super().changelist_view(request, extra_context=extra_context)

    def dashboard_view(self, request):
        qs      = Notification.objects.all()
        total   = qs.count()
        pending = qs.filter(status=NotificationStatus.PENDING).count()
        sent    = qs.filter(status=NotificationStatus.SENT).count()
        failed  = qs.filter(status=NotificationStatus.FAILED).count()
        read    = qs.filter(status=NotificationStatus.READ).count()
        unread  = qs.filter(is_read=False).count()

        cards = [
            {"label": "Total",   "value": total,   "color": "#333",    "sub": "all time"},
            {"label": "Pending", "value": pending, "color": "#fd7e14", "sub": "not yet sent"},
            {"label": "Sent",    "value": sent,    "color": "#417690", "sub": "delivered"},
            {"label": "Failed",  "value": failed,  "color": "#dc3545", "sub": "delivery error"},
            {"label": "Read",    "value": read,    "color": "#28a745", "sub": "opened by user"},
            {"label": "Unread",  "value": unread,  "color": "#6f42c1", "sub": "awaiting user"},
        ]

        # Status bar chart
        status_data = {
            "PENDING": (pending, "#fd7e14"),
            "SENT":    (sent,    "#417690"),
            "FAILED":  (failed,  "#dc3545"),
            "READ":    (read,    "#28a745"),
        }
        max_s = max((v for v, _ in status_data.values()), default=1) or 1
        status_buckets = [
            {
                "label":  label,
                "count":  count,
                "height": max(int(count / max_s * 110), 4),
                "color":  color,
            }
            for label, (count, color) in status_data.items()
        ]

        # Channel distribution bar chart
        channel_data = {
            ch: (qs.filter(channel=ch).count(), CHANNEL_COLORS.get(ch, "#999"))
            for ch in ["IN_APP", "SMS", "EMAIL", "PUSH"]
        }
        max_c = max((v for v, _ in channel_data.values()), default=1) or 1
        channel_buckets = [
            {
                "label":  label,
                "count":  count,
                "height": max(int(count / max_c * 110), 4),
                "color":  color,
                "icon":   CHANNEL_ICONS.get(label, ""),
            }
            for label, (count, color) in channel_data.items()
        ]

        # Failed notifications — last 10
        failed_notifs = (
            qs.filter(status=NotificationStatus.FAILED)
              .select_related("user")
              .order_by("-created_at")[:10]
        )
        failed_data = [
            {
                "title":      n.title,
                "user":       n.user.fullname,
                "channel":    n.channel,
                "ch_color":   CHANNEL_COLORS.get(n.channel, "#999"),
                "created_at": n.created_at,
                "detail_url": reverse("admin:notifications_notification_change", args=[n.pk]),
            }
            for n in failed_notifs
        ]

        # Users with most unread notifications — top 10
        top_unread = (
            qs.filter(is_read=False)
              .values("user__id", "user__fullname", "user__phone")
              .annotate(count=Count("id"))
              .order_by("-count")[:10]
        )
        top_unread_data = [
            {
                "fullname":   row["user__fullname"],
                "phone":      row["user__phone"],
                "count":      row["count"],
                "change_url": reverse("admin:users_user_change", args=[row["user__id"]]),
            }
            for row in top_unread
        ]

        context = dict(
            self.admin_site.each_context(request),
            title="Notifications Dashboard",
            cards=cards,
            status_buckets=status_buckets,
            channel_buckets=channel_buckets,
            failed_data=failed_data,
            top_unread_data=top_unread_data,
            broadcast_url=reverse("admin:notifications_notification_broadcast"),
        )
        return render(request, "admin/notifications/notification_dashboard.html", context)

    def broadcast_view(self, request):
        """
        Simple broadcast form — send a notification to all active users.
        Uses NotificationService.broadcast under the hood.
        """
        from apps.users.models import User

        result = None

        if request.method == "POST":
            title   = request.POST.get("title", "").strip()
            message = request.POST.get("message", "").strip()
            channel = request.POST.get("channel", "IN_APP")

            if not title or not message:
                messages.error(request, "Title and message are required.")
            else:
                users = User.objects.filter(status="active")
                NotificationService.broadcast(users, title, message)
                count = users.count()
                messages.success(request, f"Broadcast sent to {count} active user(s).")
                result = {"title": title, "message": message, "channel": channel, "count": count}

        channels = [
            {"value": ch, "label": ch, "color": CHANNEL_COLORS.get(ch, "#999")}
            for ch in ["IN_APP", "SMS", "EMAIL", "PUSH"]
        ]

        context = dict(
            self.admin_site.each_context(request),
            title="Broadcast Notification",
            channels=channels,
            result=result,
            dashboard_url=reverse("admin:notifications_notification_dashboard"),
        )
        return render(request, "admin/notifications/notification_broadcast.html", context)

    # ------------------------------------------------------------------
    # Custom display columns
    # ------------------------------------------------------------------

    @admin.display(description="ID")
    def short_id(self, obj):
        return str(obj.id)[:8] + "\u2026"

    @admin.display(description="User", ordering="user__fullname")
    def user_link(self, obj):
        url = reverse("admin:users_user_change", args=[obj.user_id])
        return format_html(
            '<a href="{}" style="font-weight:600">{}</a>'
            '<br><span style="font-size:11px;color:#aaa">{}</span>',
            url,
            obj.user.fullname,
            obj.user.phone,
        )

    @admin.display(description="Title", ordering="title")
    def title_short(self, obj):
        t = obj.title if len(obj.title) <= 40 else obj.title[:37] + "…"
        return format_html(
            '<span style="font-weight:600">{}</span>'
            '<br><span style="font-size:11px;color:#aaa">{}</span>',
            t,
            obj.message[:60] + ("…" if len(obj.message) > 60 else ""),
        )

    @admin.display(description="Channel", ordering="channel")
    def channel_display(self, obj):
        return _channel_badge(obj.channel)

    @admin.display(description="Channel")
    def channel_badge_detail(self, obj):
        return _channel_badge(obj.channel)

    @admin.display(description="Status", ordering="status")
    def status_display(self, obj):
        return _status_badge(obj.status)

    @admin.display(description="Status")
    def status_badge_detail(self, obj):
        return _status_badge(obj.status)

    @admin.display(description="Read")
    def read_icon(self, obj):
        return _bool_icon(obj.is_read)

    @admin.display(description="Metadata")
    def metadata_pretty(self, obj):
        if not obj.metadata:
            return mark_safe('<span style="color:#aaa">\u2014</span>')
        return mark_safe(
            '<pre style="background:#f8f8f8;padding:12px;border-radius:4px;'
            'font-size:12px;white-space:pre-wrap;word-break:break-all;margin:0">'
            + json.dumps(obj.metadata, indent=2, default=str)
            + "</pre>"
        )
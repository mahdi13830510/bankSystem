import json

from django.contrib import admin
from django.db.models import Count, Q
from django.shortcuts import render
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import AuditLog, AuditSeverity

# ---------------------------------------------------------------------------
# Badge helpers
# ---------------------------------------------------------------------------

SEVERITY_COLORS = {
    "INFO":     "#417690",
    "WARNING":  "#fd7e14",
    "CRITICAL": "#dc3545",
}

# Actions that are considered security-sensitive — highlighted differently
SECURITY_ACTIONS = {
    "LOGIN_FAILED", "OTP_INVALID", "OTP_EXPIRED",
    "FRAUD_DECISION", "USER_BLOCKED", "ACCOUNT_FREEZE",
    "AI_IBAN_TRANSFER", "IBAN_TRANSFER_SUCCESS",
    "ADMIN_RESET_FAILED_ATTEMPTS",
}


def _severity_badge(severity):
    color = SEVERITY_COLORS.get(severity, "#999")
    return format_html(
        '<span style="background:{};color:#fff;padding:2px 10px;border-radius:12px;'
        'font-size:11px;font-weight:600;letter-spacing:.5px">{}</span>',
        color,
        severity,
    )


def _action_display(action):
    if action in SECURITY_ACTIONS:
        return format_html(
            '<span style="color:#dc3545;font-weight:700;font-family:monospace;'
            'font-size:12px">{}</span>',
            action,
        )
    return format_html(
        '<span style="font-family:monospace;font-size:12px;color:#333">{}</span>',
        action,
    )


# ---------------------------------------------------------------------------
# AuditLogAdmin
# ---------------------------------------------------------------------------

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    change_list_template = "admin/auditlogs/auditlog_changelist.html"

    # ------------------------------------------------------------------
    # List view
    # ------------------------------------------------------------------
    list_display = (
        "short_id", "created_at", "actor_link",
        "action_display", "severity_display",
        "ip_address", "target_summary",
    )
    list_filter = (
        "severity",
        ("created_at", admin.DateFieldListFilter),
        "action",
    )
    search_fields = (
        "action", "description",
        "actor__fullname", "actor__phone",
        "ip_address", "target_type", "target_id",
    )
    ordering      = ("-created_at",)
    list_per_page = 50
    date_hierarchy = "created_at"

    # ------------------------------------------------------------------
    # Detail view — fully read-only, no add/delete
    # ------------------------------------------------------------------
    readonly_fields = (
        "id", "actor", "action", "severity_badge_detail",
        "target_type", "target_id", "description",
        "ip_address", "user_agent", "metadata_pretty", "created_at",
    )

    fieldsets = (
        ("Identity", {
            "fields": ("id", "created_at", "actor"),
        }),
        ("Event", {
            "fields": ("action", "severity_badge_detail", "description"),
        }),
        ("Target", {
            "fields": ("target_type", "target_id"),
        }),
        ("Request Info", {
            "fields": ("ip_address", "user_agent"),
            "classes": ("collapse",),
        }),
        ("Metadata", {
            "fields": ("metadata_pretty",),
            "classes": ("collapse",),
        }),
    )

    # ------------------------------------------------------------------
    # Audit logs must never be created, edited, or deleted via admin
    # ------------------------------------------------------------------

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    # ------------------------------------------------------------------
    # Extra admin views
    # ------------------------------------------------------------------

    def get_urls(self):
        urls = super().get_urls()
        extra = [
            path(
                "dashboard/",
                self.admin_site.admin_view(self.dashboard_view),
                name="auditlogs_auditlog_dashboard",
            ),
        ]
        return extra + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        qs       = AuditLog.objects.all()
        total    = qs.count()
        info     = qs.filter(severity=AuditSeverity.INFO).count()
        warning  = qs.filter(severity=AuditSeverity.WARNING).count()
        critical = qs.filter(severity=AuditSeverity.CRITICAL).count()

        extra_context["summary_cards"] = [
            {"label": "Total Logs", "value": total,    "color": "#333"},
            {"label": "Info",       "value": info,     "color": "#417690"},
            {"label": "Warning",    "value": warning,  "color": "#fd7e14"},
            {"label": "Critical",   "value": critical, "color": "#dc3545"},
        ]
        extra_context["dashboard_url"] = reverse("admin:auditlogs_auditlog_dashboard")
        return super().changelist_view(request, extra_context=extra_context)

    def dashboard_view(self, request):
        qs       = AuditLog.objects.all()
        total    = qs.count()
        info     = qs.filter(severity=AuditSeverity.INFO).count()
        warning  = qs.filter(severity=AuditSeverity.WARNING).count()
        critical = qs.filter(severity=AuditSeverity.CRITICAL).count()

        cards = [
            {"label": "Total Logs", "value": total,    "color": "#333",    "sub": "all time"},
            {"label": "Info",       "value": info,     "color": "#417690", "sub": "informational"},
            {"label": "Warning",    "value": warning,  "color": "#fd7e14", "sub": "needs attention"},
            {"label": "Critical",   "value": critical, "color": "#dc3545", "sub": "high priority"},
        ]

        # Severity bar chart
        severity_data = {
            "INFO":     (info,     "#417690"),
            "WARNING":  (warning,  "#fd7e14"),
            "CRITICAL": (critical, "#dc3545"),
        }
        max_sev = max((v for v, _ in severity_data.values()), default=1) or 1
        severity_buckets = [
            {
                "label":  label,
                "count":  count,
                "height": max(int(count / max_sev * 110), 4),
                "color":  color,
            }
            for label, (count, color) in severity_data.items()
        ]

        # Top 10 most frequent actions
        top_actions = (
            qs.values("action")
              .annotate(count=Count("id"))
              .order_by("-count")[:10]
        )
        max_action = top_actions[0]["count"] if top_actions else 1
        top_actions_data = [
            {
                "action":   row["action"],
                "count":    row["count"],
                "width":    max(int(row["count"] / max_action * 100), 2),
                "security": row["action"] in SECURITY_ACTIONS,
            }
            for row in top_actions
        ]

        # Top 10 most active actors
        top_actors = (
            qs.filter(actor__isnull=False)
              .values("actor__id", "actor__fullname", "actor__phone")
              .annotate(count=Count("id"))
              .order_by("-count")[:10]
        )
        top_actors_data = [
            {
                "fullname":  row["actor__fullname"],
                "phone":     row["actor__phone"],
                "count":     row["count"],
                "change_url": reverse("admin:users_user_change", args=[row["actor__id"]]),
            }
            for row in top_actors
        ]

        # Last 10 CRITICAL logs
        critical_logs = qs.filter(severity=AuditSeverity.CRITICAL).order_by("-created_at")[:10]
        critical_data = [
            {
                "id":         str(log.id)[:8] + "…",
                "action":     log.action,
                "actor":      log.actor.fullname if log.actor else "System",
                "ip":         log.ip_address or "—",
                "created_at": log.created_at,
                "detail_url": reverse("admin:auditlogs_auditlog_change", args=[log.pk]),
            }
            for log in critical_logs
        ]

        # Last 10 WARNING logs
        warning_logs = qs.filter(severity=AuditSeverity.WARNING).order_by("-created_at")[:10]
        warning_data = [
            {
                "id":         str(log.id)[:8] + "…",
                "action":     log.action,
                "actor":      log.actor.fullname if log.actor else "System",
                "ip":         log.ip_address or "—",
                "created_at": log.created_at,
                "detail_url": reverse("admin:auditlogs_auditlog_change", args=[log.pk]),
            }
            for log in warning_logs
        ]

        context = dict(
            self.admin_site.each_context(request),
            title="Audit Log Dashboard",
            cards=cards,
            severity_buckets=severity_buckets,
            top_actions=top_actions_data,
            top_actors=top_actors_data,
            critical_data=critical_data,
            warning_data=warning_data,
        )
        return render(request, "admin/auditlogs/auditlog_dashboard.html", context)

    # ------------------------------------------------------------------
    # Custom display columns
    # ------------------------------------------------------------------

    @admin.display(description="ID")
    def short_id(self, obj):
        return str(obj.id)[:8] + "…"

    @admin.display(description="Actor", ordering="actor__fullname")
    def actor_link(self, obj):
        if not obj.actor:
            return mark_safe('<span style="color:#aaa;font-style:italic">System</span>')
        url = reverse("admin:users_user_change", args=[obj.actor_id])
        return format_html(
            '<a href="{}" style="font-weight:600">{}</a>'
            '<br><span style="font-size:11px;color:#aaa">{}</span>',
            url,
            obj.actor.fullname,
            obj.actor.phone,
        )

    @admin.display(description="Action", ordering="action")
    def action_display(self, obj):
        return _action_display(obj.action)

    @admin.display(description="Severity", ordering="severity")
    def severity_display(self, obj):
        return _severity_badge(obj.severity)

    @admin.display(description="Severity")
    def severity_badge_detail(self, obj):
        return _severity_badge(obj.severity)

    @admin.display(description="Target")
    def target_summary(self, obj):
        if not obj.target_type and not obj.target_id:
            return mark_safe('<span style="color:#aaa">—</span>')
        return format_html(
            '<span style="font-family:monospace;font-size:12px">{} #{}</span>',
            obj.target_type,
            obj.target_id,
        )

    @admin.display(description="Metadata")
    def metadata_pretty(self, obj):
        if not obj.metadata:
            return mark_safe('<span style="color:#aaa">—</span>')
        return mark_safe(
            '<pre style="background:#f8f8f8;padding:12px;border-radius:4px;'
            'font-size:12px;white-space:pre-wrap;word-break:break-all;margin:0">'
            + json.dumps(obj.metadata, indent=2, default=str)
            + "</pre>"
        )
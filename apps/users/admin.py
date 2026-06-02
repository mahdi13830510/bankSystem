from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Count, Q
from django.shortcuts import render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import User, UserProfile, UserDevice
from .services import UserService
from apps.auditlogs.services import AuditLogService

# ---------------------------------------------------------------------------
# Badge / icon helpers
# ---------------------------------------------------------------------------

STATUS_COLORS = {
    "active":    "#28a745",
    "pending":   "#fd7e14",
    "blocked":   "#dc3545",
    "suspended": "#6c757d",
}

ROLE_COLORS = {
    "customer": "#417690",
    "employee": "#6f42c1",
    "manager":  "#fd7e14",
    "admin":    "#dc3545",
}


def _status_badge(status):
    color = STATUS_COLORS.get(status, "#999")
    return format_html(
        '<span style="background:{};color:#fff;padding:2px 10px;border-radius:12px;'
        'font-size:11px;font-weight:600;letter-spacing:.5px">{}</span>',
        color,
        status.upper(),
    )


def _role_badge(role):
    color = ROLE_COLORS.get(role, "#999")
    return format_html(
        '<span style="background:{};color:#fff;padding:2px 10px;border-radius:12px;'
        'font-size:11px;font-weight:600;letter-spacing:.5px">{}</span>',
        color,
        role.upper(),
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

@admin.action(description="Verify selected users")
def verify_users(modeladmin, request, queryset):
    updated = 0
    for user in queryset:
        UserService.verify_user(user)
        updated += 1
    messages.success(request, f"{updated} user(s) verified and set to ACTIVE.")


@admin.action(description="Block selected users")
def block_users(modeladmin, request, queryset):
    updated = 0
    for user in queryset:
        UserService.block_user(user)
        updated += 1
    messages.warning(request, f"{updated} user(s) blocked.")


@admin.action(description="Reset failed login attempts")
def reset_failed_attempts(modeladmin, request, queryset):
    updated = queryset.update(failed_login_attempts=0)
    AuditLogService.info(
        actor=request.user,
        action="ADMIN_RESET_FAILED_ATTEMPTS",
        description=f"Reset {updated} user(s)"
    )
    messages.success(request, f"Failed login attempts reset for {updated} user(s).")


@admin.action(description="Set selected users \u2192 SUSPENDED")
def suspend_users(modeladmin, request, queryset):
    updated = queryset.update(status=User.Status.SUSPENDED)
    messages.warning(request, f"{updated} user(s) suspended.")


# ---------------------------------------------------------------------------
# Inlines
# ---------------------------------------------------------------------------

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0
    fields = ("address", "city", "postal_code", "birth_date", "avatar")
    verbose_name_plural = "Profile"


class UserDeviceInline(admin.TabularInline):
    model = UserDevice
    extra = 0
    readonly_fields = ("device_name", "ip_address", "user_agent", "trusted", "last_used", "created_at")
    fields = ("device_name", "ip_address", "trusted", "last_used", "created_at")
    can_delete = False
    show_change_link = False
    verbose_name_plural = "Registered Devices"
    ordering = ("-last_used",)
    max_num = 0  # read-only — no adding from inline


# ---------------------------------------------------------------------------
# UserDeviceAdmin (standalone)
# ---------------------------------------------------------------------------

@admin.register(UserDevice)
class UserDeviceAdmin(admin.ModelAdmin):
    """
    Read-only view of devices registered automatically at login.
    Adding or deleting devices manually is intentionally disabled —
    devices are system records created by the auth flow only.
    The only field an admin may change is `trusted`.
    """
    list_display  = ("device_name", "user_link", "ip_address", "trusted_icon", "last_used", "created_at")
    list_filter   = ("trusted",)
    search_fields = ("device_name", "ip_address", "user__fullname", "user__phone")
    ordering      = ("-last_used",)
    readonly_fields = ("user", "device_name", "ip_address", "user_agent", "last_used", "created_at")
    list_per_page = 50

    fieldsets = (
        ("Device", {
            "fields": ("device_name", "ip_address", "user_agent"),
        }),
        ("User", {
            "fields": ("user",),
        }),
        ("Meta", {
            "fields": ("trusted", "last_used", "created_at"),
        }),
    )

    # ------------------------------------------------------------------
    # Disable add and delete — devices are system-created only
    # ------------------------------------------------------------------

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="User", ordering="user__fullname")
    def user_link(self, obj):
        url = reverse("admin:users_user_change", args=[obj.user_id])
        return format_html('<a href="{}">{}</a>', url, obj.user.fullname)

    @admin.display(description="Trusted")
    def trusted_icon(self, obj):
        return _bool_icon(obj.trusted)


# ---------------------------------------------------------------------------
# UserAdmin
# ---------------------------------------------------------------------------

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    change_list_template = "admin/users/user_changelist.html"

    # ------------------------------------------------------------------
    # List view
    # ------------------------------------------------------------------
    list_display = (
        "id", "fullname", "phone", "email",
        "status_display", "role_display",
        "verified_icon", "staff_icon",
        "failed_login_attempts", "date_joined",
    )
    list_filter = (
        "status", "primary_role",
        "is_verified", "is_staff",
        ("date_joined", admin.DateFieldListFilter),
    )
    search_fields = ("fullname", "phone", "email", "national_code")
    ordering      = ("-date_joined",)
    list_per_page = 40
    actions       = [verify_users, block_users, suspend_users, reset_failed_attempts]

    # ------------------------------------------------------------------
    # Detail view
    # ------------------------------------------------------------------
    readonly_fields = (
        "id", "date_joined", "last_login", "created_at", "updated_at",
        "status_badge_detail", "role_badge_detail",
        "verified_icon", "staff_icon", "is_currently_blocked",
    )

    fieldsets = (
        ("Identity", {
            "fields": ("id", "fullname", "phone", "email", "national_code"),
        }),
        ("Status & Role", {
            "fields": (
                "status", "status_badge_detail",
                "primary_role", "role_badge_detail",
                "is_verified", "verified_icon",
            ),
        }),
        ("Security", {
            "fields": (
                "password",
                "failed_login_attempts",
                "blocked_until", "is_currently_blocked",
                "last_password_change",
            ),
        }),
        ("Permissions", {
            "fields": ("is_staff", "staff_icon", "is_superuser", "groups", "user_permissions"),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": ("date_joined", "last_login", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    add_fieldsets = (
        ("Create User", {
            "classes": ("wide",),
            "fields": (
                "phone", "email", "fullname", "national_code",
                "password1", "password2",
                "primary_role", "status",
            ),
        }),
    )

    inlines = [UserProfileInline, UserDeviceInline]

    # ------------------------------------------------------------------
    # Extra admin views
    # ------------------------------------------------------------------

    def get_urls(self):
        urls = super().get_urls()
        extra = [
            path(
                "dashboard/",
                self.admin_site.admin_view(self.dashboard_view),
                name="users_user_dashboard",
            ),
        ]
        return extra + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        qs = User.objects.all()
        total     = qs.count()
        active    = qs.filter(status=User.Status.ACTIVE).count()
        pending   = qs.filter(status=User.Status.PENDING).count()
        blocked   = qs.filter(status=User.Status.BLOCKED).count()
        suspended = qs.filter(status=User.Status.SUSPENDED).count()
        verified  = qs.filter(is_verified=True).count()
        staff     = qs.filter(is_staff=True).count()

        extra_context["summary_cards"] = [
            {"label": "Total Users", "value": total,     "color": "#333"},
            {"label": "Active",      "value": active,    "color": "#28a745"},
            {"label": "Pending",     "value": pending,   "color": "#fd7e14"},
            {"label": "Blocked",     "value": blocked,   "color": "#dc3545"},
            {"label": "Suspended",   "value": suspended, "color": "#6c757d"},
            {"label": "Verified",    "value": verified,  "color": "#417690"},
            {"label": "Staff",       "value": staff,     "color": "#6f42c1"},
        ]
        extra_context["dashboard_url"] = reverse("admin:users_user_dashboard")
        return super().changelist_view(request, extra_context=extra_context)

    def dashboard_view(self, request):
        qs = User.objects.all()

        total     = qs.count()
        active    = qs.filter(status=User.Status.ACTIVE).count()
        pending   = qs.filter(status=User.Status.PENDING).count()
        blocked   = qs.filter(status=User.Status.BLOCKED).count()
        suspended = qs.filter(status=User.Status.SUSPENDED).count()
        verified  = qs.filter(is_verified=True).count()
        unverified = qs.filter(is_verified=False).count()
        staff     = qs.filter(is_staff=True).count()
        superuser = qs.filter(is_superuser=True).count()

        cards = [
            {"label": "Total Users",  "value": total,      "color": "#333",    "sub": "all statuses"},
            {"label": "Active",       "value": active,     "color": "#28a745", "sub": "fully operational"},
            {"label": "Pending",      "value": pending,    "color": "#fd7e14", "sub": "awaiting verification"},
            {"label": "Blocked",      "value": blocked,    "color": "#dc3545", "sub": "access denied"},
            {"label": "Suspended",    "value": suspended,  "color": "#6c757d", "sub": "temporarily off"},
            {"label": "Verified",     "value": verified,   "color": "#417690", "sub": "identity confirmed"},
            {"label": "Unverified",   "value": unverified, "color": "#fd7e14", "sub": "pending KYC"},
            {"label": "Staff",        "value": staff,      "color": "#6f42c1", "sub": "admin access"},
        ]

        # Status distribution bar chart
        status_data = {
            "ACTIVE":    (active,    "#28a745"),
            "PENDING":   (pending,   "#fd7e14"),
            "BLOCKED":   (blocked,   "#dc3545"),
            "SUSPENDED": (suspended, "#6c757d"),
        }
        max_count = max((v for v, _ in status_data.values()), default=1) or 1
        status_buckets = [
            {
                "label":  label,
                "count":  count,
                "height": max(int(count / max_count * 110), 4),
                "color":  color,
            }
            for label, (count, color) in status_data.items()
        ]

        # Role distribution bar chart
        role_data = {
            "CUSTOMER": (qs.filter(primary_role=User.Role.CUSTOMER).count(), "#417690"),
            "EMPLOYEE": (qs.filter(primary_role=User.Role.EMPLOYEE).count(), "#6f42c1"),
            "MANAGER":  (qs.filter(primary_role=User.Role.MANAGER).count(),  "#fd7e14"),
            "ADMIN":    (qs.filter(primary_role=User.Role.ADMIN).count(),    "#dc3545"),
        }
        max_role = max((v for v, _ in role_data.values()), default=1) or 1
        role_buckets = [
            {
                "label":  label,
                "count":  count,
                "height": max(int(count / max_role * 110), 4),
                "color":  color,
            }
            for label, (count, color) in role_data.items()
        ]

        # Recent registrations (last 10)
        recent_users = qs.order_by("-date_joined")[:10]
        recent_data = [
            {
                "fullname":   u.fullname,
                "phone":      u.phone,
                "status":     u.status,
                "role":       u.primary_role,
                "s_color":    STATUS_COLORS.get(u.status, "#999"),
                "r_color":    ROLE_COLORS.get(u.primary_role, "#999"),
                "date_joined": u.date_joined,
                "change_url": reverse("admin:users_user_change", args=[u.pk]),
            }
            for u in recent_users
        ]

        # High-risk: failed login attempts > 3
        risky_users = qs.filter(failed_login_attempts__gte=3).order_by("-failed_login_attempts")[:10]
        risky_data = [
            {
                "fullname": u.fullname,
                "phone":    u.phone,
                "attempts": u.failed_login_attempts,
                "status":   u.status,
                "s_color":  STATUS_COLORS.get(u.status, "#999"),
                "change_url": reverse("admin:users_user_change", args=[u.pk]),
            }
            for u in risky_users
        ]

        context = dict(
            self.admin_site.each_context(request),
            title="Users Dashboard",
            cards=cards,
            status_buckets=status_buckets,
            role_buckets=role_buckets,
            recent_data=recent_data,
            risky_data=risky_data,
            superuser_count=superuser,
        )
        return render(request, "admin/users/user_dashboard.html", context)

    # ------------------------------------------------------------------
    # Custom display columns
    # ------------------------------------------------------------------

    @admin.display(description="Status", ordering="status")
    def status_display(self, obj):
        return _status_badge(obj.status)

    @admin.display(description="Current Status")
    def status_badge_detail(self, obj):
        return _status_badge(obj.status)

    @admin.display(description="Role", ordering="primary_role")
    def role_display(self, obj):
        return _role_badge(obj.primary_role)

    @admin.display(description="Current Role")
    def role_badge_detail(self, obj):
        return _role_badge(obj.primary_role)

    @admin.display(description="Verified")
    def verified_icon(self, obj):
        return _bool_icon(obj.is_verified)

    @admin.display(description="Staff")
    def staff_icon(self, obj):
        return _bool_icon(obj.is_staff)

    @admin.display(description="Currently Blocked")
    def is_currently_blocked(self, obj):
        if obj.is_blocked:
            return format_html(
                '<span style="color:#dc3545;font-weight:600">Yes — until {}</span>',
                obj.blocked_until.strftime("%Y-%m-%d %H:%M"),
            )
        return mark_safe('<span style="color:#28a745;font-weight:600">No</span>')
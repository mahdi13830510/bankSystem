from django.contrib import admin, messages
from django.db.models import Count
from django.shortcuts import render
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import Bank, Branch, BankStatus
from .services.bank_service import BankService

# ---------------------------------------------------------------------------
# Status colour helpers
# ---------------------------------------------------------------------------

STATUS_COLORS = {
    "ACTIVE":      "#28a745",
    "INACTIVE":    "#6c757d",
    "MAINTENANCE": "#fd7e14",
    "SUSPENDED":   "#dc3545",
}


def _status_badge(status):
    color = STATUS_COLORS.get(status, "#999")
    return format_html(
        '<span style="background:{};color:#fff;padding:2px 10px;border-radius:12px;'
        'font-size:11px;font-weight:600;letter-spacing:.5px">{}</span>',
        color,
        status,
    )


def _bool_icon(value):
    # mark_safe is safe here — no user input involved, just a fixed icon string
    if value:
        return mark_safe(
            '<span style="color:#28a745;font-size:16px;font-weight:bold">&#10004;</span>'
        )
    return mark_safe(
        '<span style="color:#dc3545;font-size:16px;font-weight:bold">&#10008;</span>'
    )


# ---------------------------------------------------------------------------
# Bulk-status actions
# ---------------------------------------------------------------------------

@admin.action(description="Set selected banks \u2192 ACTIVE")
def activate_banks(modeladmin, request, queryset):
    updated = queryset.update(status=BankStatus.ACTIVE)
    messages.success(request, f"{updated} bank(s) set to ACTIVE.")


@admin.action(description="Set selected banks \u2192 SUSPENDED")
def suspend_banks(modeladmin, request, queryset):
    updated = queryset.update(status=BankStatus.SUSPENDED)
    messages.warning(request, f"{updated} bank(s) SUSPENDED.")


@admin.action(description="Set selected banks \u2192 MAINTENANCE")
def maintenance_banks(modeladmin, request, queryset):
    updated = queryset.update(status=BankStatus.MAINTENANCE)
    messages.info(request, f"{updated} bank(s) set to MAINTENANCE.")


@admin.action(description="Set selected banks \u2192 INACTIVE")
def deactivate_banks(modeladmin, request, queryset):
    updated = queryset.update(status=BankStatus.INACTIVE)
    messages.warning(request, f"{updated} bank(s) set to INACTIVE.")


# ---------------------------------------------------------------------------
# Branch inline
# ---------------------------------------------------------------------------

class BranchInline(admin.TabularInline):
    model = Branch
    extra = 0
    fields = ("name", "code", "city", "phone", "is_active")
    readonly_fields = ("code",)
    show_change_link = True
    ordering = ("city", "name")


# ---------------------------------------------------------------------------
# BranchAdmin
# ---------------------------------------------------------------------------

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display  = ("name", "bank_link", "code", "city", "phone", "active_icon")
    list_filter   = ("is_active", "city", "bank")
    search_fields = ("name", "code", "city", "bank__name")
    ordering      = ("bank__name", "city", "name")
    list_per_page = 50

    readonly_fields = ("id",)

    fieldsets = (
        ("Identity", {
            "fields": ("id", "bank", "name", "code"),
        }),
        ("Location", {
            "fields": ("city", "address", "phone"),
        }),
        ("Status", {
            "fields": ("is_active",),
        }),
    )

    @admin.display(description="Bank", ordering="bank__name")
    def bank_link(self, obj):
        url = reverse("admin:banks_bank_change", args=[obj.bank_id])
        return format_html('<a href="{}">{}</a>', url, obj.bank.name)

    @admin.display(description="Active")
    def active_icon(self, obj):
        return _bool_icon(obj.is_active)


# ---------------------------------------------------------------------------
# BankAdmin
# ---------------------------------------------------------------------------

@admin.register(Bank)
class BankAdmin(admin.ModelAdmin):
    change_list_template = "admin/banks/bank_changelist.html"

    list_display = (
        "short_id", "name", "code", "iban_prefix", "swift_code",
        "transfer_fee", "status_display", "instant_transfer_icon",
        "branch_count_display", "created_at",
    )
    list_filter   = ("status", "supports_instant_transfer",
                     ("created_at", admin.DateFieldListFilter))
    search_fields = ("name", "code", "swift_code", "iban_prefix")
    ordering      = ("name",)
    readonly_fields = (
        "id", "created_at", "status_badge_detail", "instant_transfer_icon",
    )
    actions       = [activate_banks, suspend_banks, maintenance_banks, deactivate_banks]
    inlines       = [BranchInline]
    list_per_page = 40

    fieldsets = (
        ("Identity", {
            "fields": ("id", "name", "code", "swift_code", "iban_prefix"),
        }),
        ("Financial Settings", {
            "fields": ("transfer_fee", "supports_instant_transfer"),
        }),
        ("Status", {
            "fields": ("status", "status_badge_detail"),
        }),
        ("Meta", {
            "fields": ("created_at",),
            "classes": ("collapse",),
        }),
    )

    # ------------------------------------------------------------------
    # Override save to use BankService + audit log (only on create)
    # ------------------------------------------------------------------

    def save_model(self, request, obj, form, change):
        if not change:
            # New bank — go through the service so audit log fires
            BankService.create_bank(
                actor=request.user,
                name=obj.name,
                code=obj.code,
                iban_prefix=obj.iban_prefix,
                swift_code=obj.swift_code,
                transfer_fee=obj.transfer_fee,
                status=obj.status,
                supports_instant_transfer=obj.supports_instant_transfer,
            )
        else:
            obj.save()

    # ------------------------------------------------------------------
    # Extra admin views: dashboard
    # ------------------------------------------------------------------

    def get_urls(self):
        urls = super().get_urls()
        extra = [
            path(
                "dashboard/",
                self.admin_site.admin_view(self.dashboard_view),
                name="banks_bank_dashboard",
            ),
        ]
        return extra + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        qs  = Bank.objects.all()
        total       = qs.count()
        active      = qs.filter(status=BankStatus.ACTIVE).count()
        suspended   = qs.filter(status=BankStatus.SUSPENDED).count()
        maintenance = qs.filter(status=BankStatus.MAINTENANCE).count()
        inactive    = qs.filter(status=BankStatus.INACTIVE).count()
        instant     = qs.filter(supports_instant_transfer=True).count()
        total_branches = Branch.objects.count()

        extra_context["summary_cards"] = [
            {"label": "Total Banks",      "value": total,          "color": "#333"},
            {"label": "Active",           "value": active,         "color": "#28a745"},
            {"label": "Suspended",        "value": suspended,      "color": "#dc3545"},
            {"label": "Maintenance",      "value": maintenance,    "color": "#fd7e14"},
            {"label": "Inactive",         "value": inactive,       "color": "#6c757d"},
            {"label": "Instant Transfer", "value": instant,        "color": "#417690"},
            {"label": "Total Branches",   "value": total_branches, "color": "#6f42c1"},
        ]
        extra_context["dashboard_url"] = reverse("admin:banks_bank_dashboard")
        return super().changelist_view(request, extra_context=extra_context)

    def dashboard_view(self, request):
        qs = Bank.objects.annotate(branch_count=Count("branches"))

        total       = qs.count()
        active      = qs.filter(status=BankStatus.ACTIVE).count()
        suspended   = qs.filter(status=BankStatus.SUSPENDED).count()
        maintenance = qs.filter(status=BankStatus.MAINTENANCE).count()
        inactive    = qs.filter(status=BankStatus.INACTIVE).count()
        instant     = qs.filter(supports_instant_transfer=True).count()
        total_branches  = Branch.objects.count()
        active_branches = Branch.objects.filter(is_active=True).count()

        cards = [
            {"label": "Total Banks",      "value": total,           "color": "#333",    "sub": "all statuses"},
            {"label": "Active",           "value": active,          "color": "#28a745", "sub": "fully operational"},
            {"label": "Suspended",        "value": suspended,       "color": "#dc3545", "sub": "requires attention"},
            {"label": "Maintenance",      "value": maintenance,     "color": "#fd7e14", "sub": "temporarily offline"},
            {"label": "Inactive",         "value": inactive,        "color": "#6c757d", "sub": "disabled"},
            {"label": "Instant Transfer", "value": instant,         "color": "#417690", "sub": "supports instant"},
            {"label": "Total Branches",   "value": total_branches,  "color": "#6f42c1", "sub": ""},
            {"label": "Active Branches",  "value": active_branches, "color": "#28a745", "sub": ""},
        ]

        # Status distribution bar chart
        status_data = {
            "ACTIVE":      (active,      "#28a745"),
            "INACTIVE":    (inactive,    "#6c757d"),
            "MAINTENANCE": (maintenance, "#fd7e14"),
            "SUSPENDED":   (suspended,   "#dc3545"),
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

        # Top active banks by branch count
        top_banks_data = [
            {"name": b.name, "count": b.branch_count, "code": b.code}
            for b in qs.filter(status=BankStatus.ACTIVE).order_by("-branch_count")[:10]
        ]

        # Transfer fee overview
        fee_data = [
            {
                "name":   b.name,
                "code":   b.code,
                "fee":    b.transfer_fee,
                "status": b.status,
                "color":  STATUS_COLORS.get(b.status, "#999"),
            }
            for b in qs.order_by("-transfer_fee")[:10]
        ]

        city_count = Branch.objects.values("city").distinct().count()

        context = dict(
            self.admin_site.each_context(request),
            title="Banks Dashboard",
            cards=cards,
            status_buckets=status_buckets,
            top_banks=top_banks_data,
            fee_data=fee_data,
            city_count=city_count,
        )
        return render(request, "admin/banks/bank_dashboard.html", context)

    # ------------------------------------------------------------------
    # Custom display columns
    # ------------------------------------------------------------------

    @admin.display(description="ID")
    def short_id(self, obj):
        return str(obj.id)[:8] + "\u2026"

    @admin.display(description="Status", ordering="status")
    def status_display(self, obj):
        return _status_badge(obj.status)

    @admin.display(description="Current Status")
    def status_badge_detail(self, obj):
        return _status_badge(obj.status)

    @admin.display(description="Instant")
    def instant_transfer_icon(self, obj):
        return _bool_icon(obj.supports_instant_transfer)

    @admin.display(description="Branches")
    def branch_count_display(self, obj):
        count = obj.branches.count()
        if count == 0:
            return mark_safe('<span style="color:#aaa">0</span>')
        url = reverse("admin:banks_branch_changelist") + f"?bank__id__exact={obj.pk}"
        return format_html('<a href="{}">{} branch(es)</a>', url, count)
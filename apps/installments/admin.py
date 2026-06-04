from decimal import Decimal

from django.contrib import admin, messages
from django.db.models import Count, Sum, Q
from django.shortcuts import render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import Installment, InstallmentStatus
from .services import InstallmentService

# ---------------------------------------------------------------------------
# Badge / colour helpers
# ---------------------------------------------------------------------------

STATUS_COLORS = {
    "PENDING": "#fd7e14",
    "PAID":    "#28a745",
    "OVERDUE": "#dc3545",
    "PARTIAL": "#17a2b8",
}


def _status_badge(status):
    color = STATUS_COLORS.get(status, "#999")
    return format_html(
        '<span style="background:{};color:#fff;padding:2px 10px;border-radius:12px;'
        'font-size:11px;font-weight:600;letter-spacing:.5px">{}</span>',
        color, status,
    )


def _bool_icon(value):
    if value:
        return mark_safe(
            '<span style="color:#28a745;font-size:16px;font-weight:bold">&#10004;</span>'
        )
    return mark_safe(
        '<span style="color:#dc3545;font-size:16px;font-weight:bold">&#10008;</span>'
    )


def _due_date_display(due_date, status):
    """
    Red   → overdue and unpaid
    Orange → due within 3 days
    Green  → paid
    Dark   → future
    """
    today = timezone.now().date()
    if status == InstallmentStatus.PAID:
        color = "#28a745"
    elif due_date < today:
        color = "#dc3545"
    elif (due_date - today).days <= 3:
        color = "#fd7e14"
    else:
        color = "#333"
    return format_html(
        '<span style="color:{};font-weight:600">{}</span>',
        color, due_date,
    )


def _amount_bar(paid_amount, total_amount):
    """Mini progress bar: paid / total."""
    if not total_amount or total_amount == 0:
        pct = 0
    else:
        pct = min(int(paid_amount / total_amount * 100), 100)
    color = "#28a745" if pct >= 100 else "#417690" if pct > 0 else "#eee"
    return format_html(
        '<div style="display:flex;align-items:center;gap:6px">'
        '<div style="background:#eee;border-radius:4px;width:60px;height:8px;overflow:hidden">'
        '<div style="background:{};height:100%;width:{}%"></div></div>'
        '<span style="font-size:11px;font-weight:600;color:{}">{}%</span>'
        '</div>',
        color, pct, color, pct,
    )


# ---------------------------------------------------------------------------
# Bulk actions
# ---------------------------------------------------------------------------

@admin.action(description="Apply penalty to selected PENDING overdue installments")
def apply_penalty_action(modeladmin, request, queryset):
    today = timezone.now().date()
    eligible = queryset.filter(
        status=InstallmentStatus.PENDING,
        due_date__lt=today,
    )
    updated = 0
    for inst in eligible:
        InstallmentService.apply_penalty(inst)
        updated += 1
    messages.warning(request, f"Penalty applied to {updated} overdue installment(s).")


@admin.action(description="Send due reminder to customers of selected installments")
def send_reminder_action(modeladmin, request, queryset):
    from apps.notifications.services import NotificationService
    from apps.notifications.templates import NotificationTemplates

    sent = 0
    for inst in queryset.filter(
        status__in=[InstallmentStatus.PENDING, InstallmentStatus.OVERDUE]
    ).select_related("loan__customer"):
        NotificationService.send_template(
            inst.loan.customer,
            NotificationTemplates.INSTALLMENT_DUE,
        )
        sent += 1
    messages.success(request, f"Due reminders sent for {sent} installment(s).")


# ---------------------------------------------------------------------------
# InstallmentAdmin
# ---------------------------------------------------------------------------

@admin.register(Installment)
class InstallmentAdmin(admin.ModelAdmin):
    change_list_template = "admin/installments/installment_changelist.html"

    # ------------------------------------------------------------------
    # List view
    # ------------------------------------------------------------------
    list_display = (
        "short_id", "loan_link", "customer_link",
        "number", "due_date_display", "status_display",
        "amount", "paid_amount", "penalty_amount",
        "progress_display", "paid_at",
    )
    list_filter = (
        "status",
        ("due_date",   admin.DateFieldListFilter),
        ("paid_at",    admin.DateFieldListFilter),
        ("created_at", admin.DateFieldListFilter),
    )
    search_fields = (
        "loan__customer__fullname",
        "loan__customer__phone",
        "loan__customer__national_code",
    )
    ordering       = ("due_date", "loan", "number")
    list_per_page  = 50
    date_hierarchy = "due_date"
    actions        = [apply_penalty_action, send_reminder_action]

    # ------------------------------------------------------------------
    # Detail view — installments are auto-generated financial records
    # ------------------------------------------------------------------
    readonly_fields = (
        "id", "loan", "number", "created_at",
        "status_badge_detail", "loan_detail_link",
        "customer_detail_link", "due_date_detail",
        "progress_bar_detail",
    )

    fieldsets = (
        ("Identity", {
            "fields": ("id", "loan_detail_link", "customer_detail_link",
                       "number", "created_at"),
        }),
        ("Schedule", {
            "fields": ("due_date", "due_date_detail", "amount"),
        }),
        ("Payment", {
            "fields": (
                "paid_amount", "penalty_amount",
                "progress_bar_detail",
                "paid_at",
            ),
        }),
        ("Status", {
            "fields": ("status", "status_badge_detail"),
        }),
    )

    def has_add_permission(self, request):
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
                name="installments_installment_dashboard",
            ),
        ]
        return extra + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        qs    = Installment.objects.all()
        today = timezone.now().date()

        total   = qs.count()
        pending = qs.filter(status=InstallmentStatus.PENDING).count()
        paid    = qs.filter(status=InstallmentStatus.PAID).count()
        overdue = qs.filter(status=InstallmentStatus.OVERDUE).count()
        partial = qs.filter(status=InstallmentStatus.PARTIAL).count()
        due_soon = qs.filter(
            status=InstallmentStatus.PENDING,
            due_date__gte=today,
            due_date__lte=today + timezone.timedelta(days=7),
        ).count()

        extra_context["summary_cards"] = [
            {"label": "Total",   "value": total,    "color": "#333"},
            {"label": "Pending", "value": pending,  "color": "#fd7e14"},
            {"label": "Paid",    "value": paid,     "color": "#28a745"},
            {"label": "Overdue", "value": overdue,  "color": "#dc3545"},
            {"label": "Partial", "value": partial,  "color": "#17a2b8"},
            {"label": "Due \u22647d", "value": due_soon, "color": "#6f42c1"},
        ]
        extra_context["dashboard_url"] = reverse(
            "admin:installments_installment_dashboard"
        )
        return super().changelist_view(request, extra_context=extra_context)

    def dashboard_view(self, request):
        qs    = Installment.objects.all()
        today = timezone.now().date()

        # --- counts ---
        total   = qs.count()
        pending = qs.filter(status=InstallmentStatus.PENDING).count()
        paid    = qs.filter(status=InstallmentStatus.PAID).count()
        overdue = qs.filter(status=InstallmentStatus.OVERDUE).count()
        partial = qs.filter(status=InstallmentStatus.PARTIAL).count()

        due_3d = qs.filter(
            status=InstallmentStatus.PENDING,
            due_date__gte=today,
            due_date__lte=today + timezone.timedelta(days=3),
        ).count()
        due_7d = qs.filter(
            status=InstallmentStatus.PENDING,
            due_date__gte=today,
            due_date__lte=today + timezone.timedelta(days=7),
        ).count()

        # --- volumes ---
        total_collected = (
            qs.filter(status=InstallmentStatus.PAID)
              .aggregate(v=Sum("paid_amount"))["v"] or Decimal("0")
        )
        total_penalty = (
            qs.aggregate(v=Sum("penalty_amount"))["v"] or Decimal("0")
        )
        total_remaining = (
            qs.filter(status__in=[
                InstallmentStatus.PENDING,
                InstallmentStatus.OVERDUE,
                InstallmentStatus.PARTIAL,
            ]).aggregate(v=Sum("amount"))["v"] or Decimal("0")
        )

        cards = [
            {"label": "Total",           "value": total,                     "color": "#333",    "sub": "all installments"},
            {"label": "Pending",         "value": pending,                   "color": "#fd7e14", "sub": "not yet paid"},
            {"label": "Paid",            "value": paid,                      "color": "#28a745", "sub": "completed"},
            {"label": "Overdue",         "value": overdue,                   "color": "#dc3545", "sub": "past due date"},
            {"label": "Partial",         "value": partial,                   "color": "#17a2b8", "sub": "partially paid"},
            {"label": "Due in 3 days",   "value": due_3d,                    "color": "#6f42c1", "sub": "urgent"},
            {"label": "Due in 7 days",   "value": due_7d,                    "color": "#6f42c1", "sub": "upcoming"},
            {"label": "Total Collected", "value": f"{total_collected:,.2f}", "color": "#28a745", "sub": "paid amounts"},
            {"label": "Total Penalties", "value": f"{total_penalty:,.2f}",   "color": "#dc3545", "sub": "accrued fines"},
            {"label": "Outstanding",     "value": f"{total_remaining:,.2f}", "color": "#fd7e14", "sub": "yet to collect"},
        ]

        # Status bar chart
        status_data = {
            "PENDING": (pending, "#fd7e14"),
            "PAID":    (paid,    "#28a745"),
            "OVERDUE": (overdue, "#dc3545"),
            "PARTIAL": (partial, "#17a2b8"),
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

        # Overdue installments — oldest due date first (most urgent), up to 15
        overdue_list = (
            qs.filter(status=InstallmentStatus.OVERDUE)
              .select_related("loan__customer")
              .order_by("due_date")[:15]
        )
        overdue_data = [
            {
                "id":           str(inst.id)[:8] + "\u2026",
                "customer":     inst.loan.customer.fullname,
                "phone":        inst.loan.customer.phone,
                "number":       inst.number,
                "due_date":     inst.due_date,
                "days_overdue": (today - inst.due_date).days,
                "amount":       inst.amount,
                "penalty":      inst.penalty_amount,
                "total_due":    inst.amount + inst.penalty_amount,
                "detail_url":   reverse(
                    "admin:installments_installment_change", args=[inst.pk]
                ),
                "loan_url":     reverse(
                    "admin:loans_loan_change", args=[inst.loan_id]
                ),
            }
            for inst in overdue_list
        ]

        # Upcoming — due in next 7 days, up to 15
        upcoming_list = (
            qs.filter(
                status=InstallmentStatus.PENDING,
                due_date__gte=today,
                due_date__lte=today + timezone.timedelta(days=7),
            )
            .select_related("loan__customer")
            .order_by("due_date")[:15]
        )
        upcoming_data = [
            {
                "customer":   inst.loan.customer.fullname,
                "phone":      inst.loan.customer.phone,
                "number":     inst.number,
                "due_date":   inst.due_date,
                "days_left":  (inst.due_date - today).days,
                "amount":     inst.amount,
                "detail_url": reverse(
                    "admin:installments_installment_change", args=[inst.pk]
                ),
            }
            for inst in upcoming_list
        ]

        # Top 10 customers with most overdue installments
        top_defaulting = (
            qs.filter(status=InstallmentStatus.OVERDUE)
              .values(
                  "loan__id",
                  "loan__customer__fullname",
                  "loan__customer__phone",
              )
              .annotate(
                  overdue_count=Count("id"),
                  total_penalty=Sum("penalty_amount"),
              )
              .order_by("-overdue_count")[:10]
        )
        top_defaulting_data = [
            {
                "customer":      row["loan__customer__fullname"],
                "phone":         row["loan__customer__phone"],
                "overdue_count": row["overdue_count"],
                "total_penalty": row["total_penalty"] or Decimal("0"),
                "loan_url":      reverse(
                    "admin:loans_loan_change", args=[row["loan__id"]]
                ),
            }
            for row in top_defaulting
        ]

        context = dict(
            self.admin_site.each_context(request),
            title="Installments Dashboard",
            cards=cards,
            status_buckets=status_buckets,
            overdue_data=overdue_data,
            upcoming_data=upcoming_data,
            top_defaulting_data=top_defaulting_data,
        )
        return render(
            request, "admin/installments/installment_dashboard.html", context
        )

    # ------------------------------------------------------------------
    # Custom display columns
    # ------------------------------------------------------------------

    @admin.display(description="ID")
    def short_id(self, obj):
        return str(obj.id)[:8] + "\u2026"

    @admin.display(description="Loan", ordering="loan__id")
    def loan_link(self, obj):
        url = reverse("admin:loans_loan_change", args=[obj.loan_id])
        return format_html(
            '<a href="{}" style="font-family:monospace;font-size:12px">{}</a>',
            url, str(obj.loan_id)[:8] + "\u2026",
        )

    @admin.display(description="Loan (detail)")
    def loan_detail_link(self, obj):
        url = reverse("admin:loans_loan_change", args=[obj.loan_id])
        return format_html('<a href="{}">Loan #{}</a>', url, str(obj.loan_id)[:8] + "\u2026")

    @admin.display(description="Customer", ordering="loan__customer__fullname")
    def customer_link(self, obj):
        url = reverse("admin:users_user_change", args=[obj.loan.customer_id])
        return format_html(
            '<a href="{}" style="font-weight:600">{}</a>'
            '<br><span style="font-size:11px;color:#aaa">{}</span>',
            url, obj.loan.customer.fullname, obj.loan.customer.phone,
        )

    @admin.display(description="Customer (detail)")
    def customer_detail_link(self, obj):
        url = reverse("admin:users_user_change", args=[obj.loan.customer_id])
        return format_html(
            '<a href="{}">{} \u2014 {}</a>',
            url, obj.loan.customer.fullname, obj.loan.customer.phone,
        )

    @admin.display(description="Due Date", ordering="due_date")
    def due_date_display(self, obj):
        return _due_date_display(obj.due_date, obj.status)

    @admin.display(description="Due Date")
    def due_date_detail(self, obj):
        return _due_date_display(obj.due_date, obj.status)

    @admin.display(description="Status", ordering="status")
    def status_display(self, obj):
        return _status_badge(obj.status)

    @admin.display(description="Status")
    def status_badge_detail(self, obj):
        return _status_badge(obj.status)

    @admin.display(description="Progress", ordering="paid_amount")
    def progress_display(self, obj):
        return _amount_bar(obj.paid_amount, obj.amount + obj.penalty_amount)

    @admin.display(description="Payment Progress")
    def progress_bar_detail(self, obj):
        return _amount_bar(obj.paid_amount, obj.amount + obj.penalty_amount)
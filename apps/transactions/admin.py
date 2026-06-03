from decimal import Decimal

from django.contrib import admin, messages
from django.db.models import Count, Sum, Q
from django.shortcuts import render
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import Transaction, TransactionType, TransactionStatus

# ---------------------------------------------------------------------------
# Badge helpers
# ---------------------------------------------------------------------------

STATUS_COLORS = {
    "PENDING":  "#fd7e14",
    "SUCCESS":  "#28a745",
    "FAILED":   "#dc3545",
    "BLOCKED":  "#6c757d",
    "REVERSED": "#6f42c1",
}

TYPE_COLORS = {
    "CARD_TO_CARD":       "#417690",
    "INTERNAL_TRANSFER":  "#17a2b8",
    "IBAN_TRANSFER":      "#6f42c1",
    "CASH_DEPOSIT":       "#28a745",
    "CASH_WITHDRAW":      "#fd7e14",
    "LOAN_DISBURSEMENT":  "#20c997",
    "INSTALLMENT_PAYMENT":"#6c757d",
    "LATE_FEE":           "#dc3545",
    "LOAN_SETTLEMENT":    "#fd7e14",
    "REFUND":             "#e83e8c",
}

# Types that move money between accounts — higher scrutiny
TRANSFER_TYPES = {
    "CARD_TO_CARD",
    "INTERNAL_TRANSFER",
    "IBAN_TRANSFER",
}


def _status_badge(status):
    color = STATUS_COLORS.get(status, "#999")
    return format_html(
        '<span style="background:{};color:#fff;padding:2px 10px;border-radius:12px;'
        'font-size:11px;font-weight:600;letter-spacing:.5px">{}</span>',
        color,
        status,
    )


def _type_badge(txn_type):
    color = TYPE_COLORS.get(txn_type, "#999")
    label = txn_type.replace("_", " ")
    return format_html(
        '<span style="background:{};color:#fff;padding:2px 9px;border-radius:12px;'
        'font-size:11px;font-weight:600;letter-spacing:.4px">{}</span>',
        color,
        label,
    )


def _amount_display(amount, fee=None):
    """Format amount with optional fee in grey beneath."""
    if fee and fee > 0:
        return format_html(
            '<span style="font-weight:700;font-family:monospace">{}</span>'
            '<br><span style="font-size:11px;color:#aaa;font-family:monospace">'
            'fee: {}</span>',
            amount,
            fee,
        )
    return format_html(
        '<span style="font-weight:700;font-family:monospace">{}</span>',
        amount,
    )


# ---------------------------------------------------------------------------
# Bulk actions
# ---------------------------------------------------------------------------

@admin.action(description="Mark selected transactions as REVERSED")
def reverse_transactions(modeladmin, request, queryset):
    allowed = queryset.filter(status=TransactionStatus.SUCCESS)
    updated = allowed.update(status=TransactionStatus.REVERSED)
    messages.warning(request, f"{updated} transaction(s) marked as REVERSED.")


@admin.action(description="Mark selected transactions as FAILED")
def fail_transactions(modeladmin, request, queryset):
    allowed = queryset.filter(status=TransactionStatus.PENDING)
    updated = allowed.update(status=TransactionStatus.FAILED)
    messages.warning(request, f"{updated} PENDING transaction(s) marked as FAILED.")


# ---------------------------------------------------------------------------
# TransactionAdmin
# ---------------------------------------------------------------------------

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    change_list_template = "admin/transactions/transaction_changelist.html"

    # ------------------------------------------------------------------
    # List view
    # ------------------------------------------------------------------
    list_display = (
        "short_id", "reference_number", "account_link",
        "type_display", "status_display",
        "amount_display", "created_at",
    )
    list_filter = (
        "status",
        "type",
        ("created_at", admin.DateFieldListFilter),
    )
    search_fields = (
        "reference_number", "description",
        "account__account_number", "account__iban",
        "account__customer__fullname", "account__customer__phone",
    )
    ordering       = ("-created_at",)
    list_per_page  = 50
    date_hierarchy = "created_at"
    actions        = [reverse_transactions, fail_transactions]

    # ------------------------------------------------------------------
    # Detail view — transactions are immutable financial records
    # ------------------------------------------------------------------
    readonly_fields = (
        "id", "account", "amount", "fee", "type",
        "reference_number", "description", "created_at",
        "status_badge_detail", "type_badge_detail",
        "account_detail_link", "total_charged",
    )

    fieldsets = (
        ("Identity", {
            "fields": ("id", "reference_number", "created_at"),
        }),
        ("Account", {
            "fields": ("account", "account_detail_link"),
        }),
        ("Transaction", {
            "fields": (
                "type", "type_badge_detail",
                "amount", "fee", "total_charged",
                "description",
            ),
        }),
        ("Status", {
            "fields": ("status", "status_badge_detail"),
        }),
    )

    # Transactions are immutable financial records — no manual creation
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
                name="transactions_transaction_dashboard",
            ),
        ]
        return extra + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        qs = Transaction.objects.all()
        total    = qs.count()
        success  = qs.filter(status=TransactionStatus.SUCCESS).count()
        pending  = qs.filter(status=TransactionStatus.PENDING).count()
        failed   = qs.filter(status=TransactionStatus.FAILED).count()
        blocked  = qs.filter(status=TransactionStatus.BLOCKED).count()
        reversed_ = qs.filter(status=TransactionStatus.REVERSED).count()

        total_volume = (
            qs.filter(status=TransactionStatus.SUCCESS)
              .aggregate(v=Sum("amount"))["v"] or Decimal("0")
        )
        total_fees = (
            qs.filter(status=TransactionStatus.SUCCESS)
              .aggregate(f=Sum("fee"))["f"] or Decimal("0")
        )

        extra_context["summary_cards"] = [
            {"label": "Total",    "value": total,             "color": "#333"},
            {"label": "Success",  "value": success,           "color": "#28a745"},
            {"label": "Pending",  "value": pending,           "color": "#fd7e14"},
            {"label": "Failed",   "value": failed,            "color": "#dc3545"},
            {"label": "Blocked",  "value": blocked,           "color": "#6c757d"},
            {"label": "Reversed", "value": reversed_,         "color": "#6f42c1"},
            {"label": "Volume",   "value": f"{total_volume:,.2f}", "color": "#28a745"},
            {"label": "Fees",     "value": f"{total_fees:,.2f}",   "color": "#417690"},
        ]
        extra_context["dashboard_url"] = reverse("admin:transactions_transaction_dashboard")
        return super().changelist_view(request, extra_context=extra_context)

    def dashboard_view(self, request):
        qs = Transaction.objects.all()

        # --- counts ---
        total     = qs.count()
        success   = qs.filter(status=TransactionStatus.SUCCESS).count()
        pending   = qs.filter(status=TransactionStatus.PENDING).count()
        failed    = qs.filter(status=TransactionStatus.FAILED).count()
        blocked   = qs.filter(status=TransactionStatus.BLOCKED).count()
        reversed_ = qs.filter(status=TransactionStatus.REVERSED).count()

        # --- volume & fees (success only) ---
        success_qs    = qs.filter(status=TransactionStatus.SUCCESS)
        total_volume  = success_qs.aggregate(v=Sum("amount"))["v"] or Decimal("0")
        total_fees    = success_qs.aggregate(f=Sum("fee"))["f"] or Decimal("0")
        transfer_vol  = (
            success_qs.filter(type__in=TRANSFER_TYPES)
                      .aggregate(v=Sum("amount"))["v"] or Decimal("0")
        )

        cards = [
            {"label": "Total Transactions", "value": total,                     "color": "#333",    "sub": "all time"},
            {"label": "Successful",         "value": success,                   "color": "#28a745", "sub": "completed"},
            {"label": "Pending",            "value": pending,                   "color": "#fd7e14", "sub": "in progress"},
            {"label": "Failed",             "value": failed,                    "color": "#dc3545", "sub": "errors"},
            {"label": "Blocked",            "value": blocked,                   "color": "#6c757d", "sub": "by fraud"},
            {"label": "Reversed",           "value": reversed_,                 "color": "#6f42c1", "sub": "rolled back"},
            {"label": "Total Volume",       "value": f"{total_volume:,.2f}",    "color": "#28a745", "sub": "success txns"},
            {"label": "Total Fees",         "value": f"{total_fees:,.2f}",      "color": "#417690", "sub": "revenue"},
            {"label": "Transfer Volume",    "value": f"{transfer_vol:,.2f}",    "color": "#17a2b8", "sub": "p2p transfers"},
        ]

        # Status bar chart
        status_data = {
            "SUCCESS":  (success,   "#28a745"),
            "PENDING":  (pending,   "#fd7e14"),
            "FAILED":   (failed,    "#dc3545"),
            "BLOCKED":  (blocked,   "#6c757d"),
            "REVERSED": (reversed_, "#6f42c1"),
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

        # Type distribution — horizontal bar chart
        type_rows = (
            qs.values("type")
              .annotate(count=Count("id"), volume=Sum("amount"))
              .order_by("-count")
        )
        max_type = type_rows[0]["count"] if type_rows else 1
        type_data = [
            {
                "type":    row["type"],
                "label":   row["type"].replace("_", " "),
                "count":   row["count"],
                "volume":  row["volume"] or Decimal("0"),
                "width":   max(int(row["count"] / max_type * 100), 2),
                "color":   TYPE_COLORS.get(row["type"], "#999"),
            }
            for row in type_rows
        ]

        # Last 10 FAILED transactions
        failed_txns = (
            qs.filter(status=TransactionStatus.FAILED)
              .select_related("account__customer")
              .order_by("-created_at")[:10]
        )
        failed_data = [
            {
                "ref":        t.reference_number,
                "type":       t.type.replace("_", " "),
                "t_color":    TYPE_COLORS.get(t.type, "#999"),
                "amount":     t.amount,
                "account":    t.account.account_number,
                "customer":   t.account.customer.fullname,
                "created_at": t.created_at,
                "detail_url": reverse("admin:transactions_transaction_change", args=[t.pk]),
            }
            for t in failed_txns
        ]

        # Last 10 BLOCKED transactions
        blocked_txns = (
            qs.filter(status=TransactionStatus.BLOCKED)
              .select_related("account__customer")
              .order_by("-created_at")[:10]
        )
        blocked_data = [
            {
                "ref":        t.reference_number,
                "type":       t.type.replace("_", " "),
                "t_color":    TYPE_COLORS.get(t.type, "#999"),
                "amount":     t.amount,
                "account":    t.account.account_number,
                "customer":   t.account.customer.fullname,
                "created_at": t.created_at,
                "detail_url": reverse("admin:transactions_transaction_change", args=[t.pk]),
            }
            for t in blocked_txns
        ]

        # Top 10 accounts by transaction count
        top_accounts = (
            qs.values(
                "account__id",
                "account__account_number",
                "account__customer__fullname",
            )
            .annotate(count=Count("id"), volume=Sum("amount"))
            .order_by("-count")[:10]
        )
        top_accounts_data = [
            {
                "account_number": row["account__account_number"],
                "customer":       row["account__customer__fullname"],
                "count":          row["count"],
                "volume":         row["volume"] or Decimal("0"),
                "account_url":    reverse(
                    "admin:accounts_account_change",
                    args=[row["account__id"]]
                ),
            }
            for row in top_accounts
        ]

        context = dict(
            self.admin_site.each_context(request),
            title="Transactions Dashboard",
            cards=cards,
            status_buckets=status_buckets,
            type_data=type_data,
            failed_data=failed_data,
            blocked_data=blocked_data,
            top_accounts_data=top_accounts_data,
        )
        return render(request, "admin/transactions/transaction_dashboard.html", context)

    # ------------------------------------------------------------------
    # Custom display columns
    # ------------------------------------------------------------------

    @admin.display(description="ID")
    def short_id(self, obj):
        return str(obj.id)[:8] + "\u2026"

    @admin.display(description="Account", ordering="account__account_number")
    def account_link(self, obj):
        url = reverse("admin:accounts_account_change", args=[obj.account_id])
        return format_html(
            '<a href="{}" style="font-weight:600;font-family:monospace">{}</a>'
            '<br><span style="font-size:11px;color:#aaa">{}</span>',
            url,
            obj.account.account_number,
            obj.account.customer.fullname,
        )

    @admin.display(description="Account (detail)")
    def account_detail_link(self, obj):
        url = reverse("admin:accounts_account_change", args=[obj.account_id])
        return format_html(
            '<a href="{}">{} — {}</a>',
            url,
            obj.account.account_number,
            obj.account.customer.fullname,
        )

    @admin.display(description="Type", ordering="type")
    def type_display(self, obj):
        return _type_badge(obj.type)

    @admin.display(description="Type")
    def type_badge_detail(self, obj):
        return _type_badge(obj.type)

    @admin.display(description="Status", ordering="status")
    def status_display(self, obj):
        return _status_badge(obj.status)

    @admin.display(description="Status")
    def status_badge_detail(self, obj):
        return _status_badge(obj.status)

    @admin.display(description="Amount", ordering="amount")
    def amount_display(self, obj):
        return _amount_display(obj.amount, obj.fee)

    @admin.display(description="Total Charged")
    def total_charged(self, obj):
        total = obj.amount + (obj.fee or Decimal("0"))
        return format_html(
            '<span style="font-weight:700;font-family:monospace;font-size:14px">{}</span>',
            total,
        )
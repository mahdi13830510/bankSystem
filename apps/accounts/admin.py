from decimal import Decimal

from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db.models import Count, Sum, Q
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import Account, AccountStatus, AccountType, CurrencyType
from .services import AccountService

# ---------------------------------------------------------------------------
# Badge / colour helpers
# ---------------------------------------------------------------------------

STATUS_COLORS = {
    "ACTIVE":  "#28a745",
    "BLOCKED": "#dc3545",
    "CLOSED":  "#6c757d",
}

TYPE_COLORS = {
    "SAVING":   "#417690",
    "CURRENT":  "#6f42c1",
    "BUSINESS": "#fd7e14",
}

CURRENCY_COLORS = {
    "TRY": "#28a745",
    "USD": "#17a2b8",
    "EUR": "#6f42c1",
}


def _status_badge(status):
    color = STATUS_COLORS.get(status, "#999")
    return format_html(
        '<span style="background:{};color:#fff;padding:2px 10px;border-radius:12px;'
        'font-size:11px;font-weight:600;letter-spacing:.5px">{}</span>',
        color, status,
    )


def _type_badge(acc_type):
    color = TYPE_COLORS.get(acc_type, "#999")
    return format_html(
        '<span style="background:{};color:#fff;padding:2px 10px;border-radius:12px;'
        'font-size:11px;font-weight:600;letter-spacing:.5px">{}</span>',
        color, acc_type,
    )


def _currency_badge(currency):
    color = CURRENCY_COLORS.get(currency, "#999")
    return format_html(
        '<span style="background:{};color:#fff;padding:2px 10px;border-radius:12px;'
        'font-size:11px;font-weight:600;letter-spacing:.5px">{}</span>',
        color, currency,
    )


def _bool_icon(value):
    if value:
        return mark_safe(
            '<span style="color:#28a745;font-size:16px;font-weight:bold">&#10004;</span>'
        )
    return mark_safe(
        '<span style="color:#dc3545;font-size:16px;font-weight:bold">&#10008;</span>'
    )


def _balance_display(balance, blocked=None, loan_blocked=None):
    """Main balance bold + blocked amounts beneath in grey."""
    html = format_html(
        '<span style="font-weight:700;font-family:monospace;font-size:13px">{}</span>',
        balance,
    )
    details = []
    if blocked and blocked > 0:
        details.append(f"blocked: {blocked}")
    if loan_blocked and loan_blocked > 0:
        details.append(f"loan: {loan_blocked}")
    if details:
        html = html + format_html(
            '<br><span style="font-size:11px;color:#aaa;font-family:monospace">{}</span>',
            "  |  ".join(details),
        )
    return html


# ---------------------------------------------------------------------------
# Bulk actions
# ---------------------------------------------------------------------------

@admin.action(description="Freeze (BLOCK) selected ACTIVE accounts")
def freeze_accounts(modeladmin, request, queryset):
    updated = 0
    for acc in queryset.filter(status=AccountStatus.ACTIVE):
        AccountService.freeze(acc.id, actor=request.user)
        updated += 1
    messages.warning(request, f"{updated} account(s) frozen.")


@admin.action(description="Activate selected BLOCKED accounts")
def activate_accounts(modeladmin, request, queryset):
    updated = 0
    for acc in queryset.filter(status=AccountStatus.BLOCKED):
        AccountService.activate(acc.id, actor=request.user)
        updated += 1
    messages.success(request, f"{updated} account(s) activated.")


@admin.action(description="Close selected accounts (balance must be zero)")
def close_accounts(modeladmin, request, queryset):
    closed = 0
    skipped = 0
    for acc in queryset.exclude(status=AccountStatus.CLOSED):
        try:
            AccountService.close(acc.id, actor=request.user)
            closed += 1
        except ValidationError:
            skipped += 1
    if closed:
        messages.success(request, f"{closed} account(s) closed.")
    if skipped:
        messages.warning(request, f"{skipped} account(s) skipped (non-zero balance).")


# ---------------------------------------------------------------------------
# AccountAdmin
# ---------------------------------------------------------------------------

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    change_list_template = "admin/accounts/account_changelist.html"

    # ------------------------------------------------------------------
    # List view
    # ------------------------------------------------------------------
    list_display = (
        "id", "account_number_display", "customer_link",
        "bank_link", "type_display", "currency_display",
        "balance_display", "status_display",
        "primary_icon", "created_at",
    )
    list_filter = (
        "status", "type", "currency", "is_primary",
        "bank",
        ("created_at", admin.DateFieldListFilter),
    )
    search_fields = (
        "account_number", "iban",
        "customer__fullname", "customer__phone",
        "customer__national_code",
        "bank__name",
    )
    ordering       = ("-id",)
    list_per_page  = 40
    date_hierarchy = "created_at"
    actions        = [freeze_accounts, activate_accounts, close_accounts]

    # ------------------------------------------------------------------
    # Detail / Add views
    # ------------------------------------------------------------------
    readonly_fields = (
        "id", "account_number", "iban", "created_at",
        "status_badge_detail", "type_badge_detail",
        "currency_badge_detail", "primary_icon",
        "available_balance_display",
        "customer_detail_link", "bank_detail_link",
        "transactions_link",
    )

    # CHANGE: everything about the account is shown, most fields locked
    fieldsets = (
        ("Identity", {
            "fields": (
                "id", "account_number", "iban",
                "customer_detail_link", "bank_detail_link",
                "created_at",
            ),
        }),
        ("Classification", {
            "fields": (
                "type", "type_badge_detail",
                "currency", "currency_badge_detail",
                "is_primary", "primary_icon",
            ),
        }),
        ("Balance", {
            "fields": (
                "balance", "blocked_balance",
                "loan_blocked_balance",
                "available_balance_display",
            ),
        }),
        ("Status", {
            "fields": ("status", "status_badge_detail"),
        }),
        ("Transactions", {
            "fields": ("transactions_link",),
        }),
    )

    # ADD: open account for a customer via AccountService
    add_fieldsets = (
        ("Customer & Bank", {
            "description": (
                "Select the customer and bank. "
                "Account number and IBAN will be generated automatically."
            ),
            "fields": ("customer", "bank"),
        }),
        ("Account Details", {
            "fields": ("type", "currency", "is_primary"),
        }),
    )

    raw_id_fields = ("customer",)

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            # ADD — only computed display fields are readonly
            return (
                "status_badge_detail", "type_badge_detail",
                "currency_badge_detail", "primary_icon",
                "available_balance_display", "customer_detail_link",
                "bank_detail_link", "transactions_link",
            )
        return self.readonly_fields

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.add_fieldsets
        return self.fieldsets

    def save_model(self, request, obj, form, change):
        if not change:
            # Route through AccountService so account_number/IBAN are
            # generated correctly and audit log fires.
            AccountService.open_account(
                user=obj.customer,
                bank_id=obj.bank_id,
                type=obj.type,
                currency=obj.currency,
            )
            # Don't call super().save_model — service already saved it.
        else:
            obj.save()

    # ------------------------------------------------------------------
    # Status-change custom URLs (Freeze / Activate / Close / Deposit / Withdraw)
    # ------------------------------------------------------------------

    def get_urls(self):
        urls = super().get_urls()
        extra = [
            path(
                "dashboard/",
                self.admin_site.admin_view(self.dashboard_view),
                name="accounts_account_dashboard",
            ),
            path(
                "<int:pk>/freeze/",
                self.admin_site.admin_view(self.freeze_view),
                name="accounts_account_freeze",
            ),
            path(
                "<int:pk>/activate/",
                self.admin_site.admin_view(self.activate_view),
                name="accounts_account_activate",
            ),
            path(
                "<int:pk>/close/",
                self.admin_site.admin_view(self.close_view),
                name="accounts_account_close",
            ),
            path(
                "<int:pk>/deposit/",
                self.admin_site.admin_view(self.deposit_view),
                name="accounts_account_deposit",
            ),
            path(
                "<int:pk>/withdraw/",
                self.admin_site.admin_view(self.withdraw_view),
                name="accounts_account_withdraw",
            ),
            path(
                "<int:pk>/set-primary/",
                self.admin_site.admin_view(self.set_primary_view),
                name="accounts_account_set_primary",
            ),
        ]
        return extra + urls

    # ---- one-click status actions ----

    def freeze_view(self, request, pk):
        try:
            AccountService.freeze(pk, actor=request.user)
            messages.warning(request, "Account frozen.")
        except Exception as e:
            messages.error(request, str(e))
        return redirect(reverse("admin:accounts_account_change", args=[pk]))

    def activate_view(self, request, pk):
        try:
            AccountService.activate(pk, actor=request.user)
            messages.success(request, "Account activated.")
        except Exception as e:
            messages.error(request, str(e))
        return redirect(reverse("admin:accounts_account_change", args=[pk]))

    def close_view(self, request, pk):
        try:
            AccountService.close(pk, actor=request.user)
            messages.success(request, "Account closed.")
        except ValidationError as e:
            messages.error(request, str(e))
        return redirect(reverse("admin:accounts_account_change", args=[pk]))

    def set_primary_view(self, request, pk):
        account = Account.objects.get(pk=pk)
        try:
            AccountService.set_primary(
                user=account.customer,
                account_id=pk,
                actor=request.user,
            )
            messages.success(request, "Primary account updated.")
        except ValidationError as e:
            messages.error(request, str(e))
        return redirect(reverse("admin:accounts_account_change", args=[pk]))

    # ---- deposit / withdraw (POST form) ----

    def _balance_op_view(self, request, pk, operation):
        """
        Shared view for deposit and withdraw.
        operation: "deposit" | "withdraw"
        """
        account = Account.objects.select_related("customer", "bank").get(pk=pk)

        if request.method == "POST":
            try:
                amount = Decimal(request.POST.get("amount", "0"))
                if amount <= 0:
                    raise ValidationError("Amount must be positive.")
                if operation == "deposit":
                    AccountService.increase_balance(
                        account_id=pk, amount=amount, actor=request.user
                    )
                    messages.success(request, f"Deposited {amount} to account.")
                else:
                    AccountService.withdraw(
                        account_id=pk, amount=amount, actor=request.user
                    )
                    messages.success(request, f"Withdrew {amount} from account.")
                return redirect(reverse("admin:accounts_account_change", args=[pk]))
            except (ValidationError, Exception) as e:
                messages.error(request, str(e))

        context = dict(
            self.admin_site.each_context(request),
            title=f"{'Deposit to' if operation == 'deposit' else 'Withdraw from'} Account",
            account=account,
            operation=operation,
            back_url=reverse("admin:accounts_account_change", args=[pk]),
        )
        return render(request, "admin/accounts/account_balance_op.html", context)

    def deposit_view(self, request, pk):
        return self._balance_op_view(request, pk, "deposit")

    def withdraw_view(self, request, pk):
        return self._balance_op_view(request, pk, "withdraw")

    # ------------------------------------------------------------------
    # Inject action buttons into the change form
    # ------------------------------------------------------------------

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        try:
            account = Account.objects.get(pk=object_id)
            extra_context["account_status"] = account.status
            extra_context["is_primary"]     = account.is_primary

            if account.status == AccountStatus.ACTIVE:
                extra_context["freeze_url"]  = reverse(
                    "admin:accounts_account_freeze", args=[object_id]
                )
                extra_context["deposit_url"] = reverse(
                    "admin:accounts_account_deposit", args=[object_id]
                )
                extra_context["withdraw_url"] = reverse(
                    "admin:accounts_account_withdraw", args=[object_id]
                )
                if not account.is_primary:
                    extra_context["set_primary_url"] = reverse(
                        "admin:accounts_account_set_primary", args=[object_id]
                    )

            if account.status == AccountStatus.BLOCKED:
                extra_context["activate_url"] = reverse(
                    "admin:accounts_account_activate", args=[object_id]
                )

            if account.status in (AccountStatus.ACTIVE, AccountStatus.BLOCKED):
                extra_context["close_url"] = reverse(
                    "admin:accounts_account_close", args=[object_id]
                )
        except Account.DoesNotExist:
            pass
        return super().change_view(
            request, object_id, form_url, extra_context=extra_context
        )

    # ------------------------------------------------------------------
    # Dashboard view
    # ------------------------------------------------------------------

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        qs = Account.objects.all()

        total   = qs.count()
        active  = qs.filter(status=AccountStatus.ACTIVE).count()
        blocked = qs.filter(status=AccountStatus.BLOCKED).count()
        closed  = qs.filter(status=AccountStatus.CLOSED).count()
        primary = qs.filter(is_primary=True).count()

        total_balance = (
            qs.filter(status=AccountStatus.ACTIVE)
              .aggregate(v=Sum("balance"))["v"] or Decimal("0")
        )

        extra_context["summary_cards"] = [
            {"label": "Total",   "value": total,                     "color": "#333"},
            {"label": "Active",  "value": active,                    "color": "#28a745"},
            {"label": "Blocked", "value": blocked,                   "color": "#dc3545"},
            {"label": "Closed",  "value": closed,                    "color": "#6c757d"},
            {"label": "Primary", "value": primary,                   "color": "#417690"},
            {"label": "Balance", "value": f"{total_balance:,.2f}",   "color": "#28a745"},
        ]
        extra_context["dashboard_url"] = reverse("admin:accounts_account_dashboard")
        return super().changelist_view(request, extra_context=extra_context)

    def dashboard_view(self, request):
        qs = Account.objects.all()

        total   = qs.count()
        active  = qs.filter(status=AccountStatus.ACTIVE).count()
        blocked = qs.filter(status=AccountStatus.BLOCKED).count()
        closed  = qs.filter(status=AccountStatus.CLOSED).count()
        primary = qs.filter(is_primary=True).count()

        agg = qs.filter(status=AccountStatus.ACTIVE).aggregate(
            total_balance=Sum("balance"),
            total_blocked=Sum("blocked_balance"),
            total_loan_blocked=Sum("loan_blocked_balance"),
        )
        total_balance      = agg["total_balance"]      or Decimal("0")
        total_blocked_bal  = agg["total_blocked"]      or Decimal("0")
        total_loan_blocked = agg["total_loan_blocked"] or Decimal("0")
        available          = total_balance - total_blocked_bal

        cards = [
            {"label": "Total Accounts",   "value": total,                       "color": "#333",    "sub": "all statuses"},
            {"label": "Active",           "value": active,                      "color": "#28a745", "sub": "operational"},
            {"label": "Blocked",          "value": blocked,                     "color": "#dc3545", "sub": "frozen"},
            {"label": "Closed",           "value": closed,                      "color": "#6c757d", "sub": "terminated"},
            {"label": "Primary Accounts", "value": primary,                     "color": "#417690", "sub": "one per customer"},
            {"label": "Total Balance",    "value": f"{total_balance:,.2f}",     "color": "#28a745", "sub": "active accounts"},
            {"label": "Blocked Balance",  "value": f"{total_blocked_bal:,.2f}", "color": "#dc3545", "sub": "on hold"},
            {"label": "Available",        "value": f"{available:,.2f}",         "color": "#17a2b8", "sub": "free to use"},
        ]

        # Status bar chart
        status_data = {
            "ACTIVE":  (active,  "#28a745"),
            "BLOCKED": (blocked, "#dc3545"),
            "CLOSED":  (closed,  "#6c757d"),
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

        # Type distribution — horizontal bars
        type_rows = (
            qs.values("type")
              .annotate(count=Count("id"), total_balance=Sum("balance"))
              .order_by("-count")
        )
        max_t = type_rows[0]["count"] if type_rows else 1
        type_data = [
            {
                "type":    row["type"],
                "count":   row["count"],
                "balance": row["total_balance"] or Decimal("0"),
                "width":   max(int(row["count"] / max_t * 100), 2),
                "color":   TYPE_COLORS.get(row["type"], "#999"),
            }
            for row in type_rows
        ]

        # Currency distribution — horizontal bars
        currency_rows = (
            qs.values("currency")
              .annotate(count=Count("id"), total_balance=Sum("balance"))
              .order_by("-count")
        )
        max_c = currency_rows[0]["count"] if currency_rows else 1
        currency_data = [
            {
                "currency": row["currency"],
                "count":    row["count"],
                "balance":  row["total_balance"] or Decimal("0"),
                "width":    max(int(row["count"] / max_c * 100), 2),
                "color":    CURRENCY_COLORS.get(row["currency"], "#999"),
            }
            for row in currency_rows
        ]

        # Top 10 accounts by balance
        top_balance = (
            qs.filter(status=AccountStatus.ACTIVE)
              .select_related("customer", "bank")
              .order_by("-balance")[:10]
        )
        top_balance_data = [
            {
                "account_number": acc.account_number,
                "customer":       acc.customer.fullname,
                "bank":           acc.bank.name,
                "currency":       acc.currency,
                "cur_color":      CURRENCY_COLORS.get(acc.currency, "#999"),
                "balance":        acc.balance,
                "change_url":     reverse("admin:accounts_account_change", args=[acc.pk]),
                "customer_url":   reverse("admin:users_user_change", args=[acc.customer_id]),
            }
            for acc in top_balance
        ]

        # Recently blocked accounts (last 10)
        blocked_accounts = (
            qs.filter(status=AccountStatus.BLOCKED)
              .select_related("customer", "bank")
              .order_by("-id")[:10]
        )
        blocked_data = [
            {
                "account_number": acc.account_number,
                "customer":       acc.customer.fullname,
                "phone":          acc.customer.phone,
                "bank":           acc.bank.name,
                "balance":        acc.balance,
                "change_url":     reverse("admin:accounts_account_change", args=[acc.pk]),
            }
            for acc in blocked_accounts
        ]

        context = dict(
            self.admin_site.each_context(request),
            title="Accounts Dashboard",
            cards=cards,
            status_buckets=status_buckets,
            type_data=type_data,
            currency_data=currency_data,
            top_balance_data=top_balance_data,
            blocked_data=blocked_data,
        )
        return render(request, "admin/accounts/account_dashboard.html", context)

    # ------------------------------------------------------------------
    # Custom display columns
    # ------------------------------------------------------------------

    @admin.display(description="Account #", ordering="account_number")
    def account_number_display(self, obj):
        return format_html(
            '<span style="font-family:monospace;font-weight:600">{}</span>'
            '<br><span style="font-size:10px;color:#aaa;font-family:monospace">{}</span>',
            obj.account_number,
            obj.iban,
        )

    @admin.display(description="Customer", ordering="customer__fullname")
    def customer_link(self, obj):
        url = reverse("admin:users_user_change", args=[obj.customer_id])
        return format_html(
            '<a href="{}" style="font-weight:600">{}</a>'
            '<br><span style="font-size:11px;color:#aaa">{}</span>',
            url, obj.customer.fullname, obj.customer.phone,
        )

    @admin.display(description="Customer")
    def customer_detail_link(self, obj):
        url = reverse("admin:users_user_change", args=[obj.customer_id])
        return format_html(
            '<a href="{}">{} \u2014 {}</a>',
            url, obj.customer.fullname, obj.customer.phone,
        )

    @admin.display(description="Bank", ordering="bank__name")
    def bank_link(self, obj):
        url = reverse("admin:banks_bank_change", args=[obj.bank_id])
        return format_html('<a href="{}">{}</a>', url, obj.bank.name)

    @admin.display(description="Bank")
    def bank_detail_link(self, obj):
        url = reverse("admin:banks_bank_change", args=[obj.bank_id])
        return format_html('<a href="{}">{}</a>', url, obj.bank.name)

    @admin.display(description="Type", ordering="type")
    def type_display(self, obj):
        return _type_badge(obj.type)

    @admin.display(description="Type")
    def type_badge_detail(self, obj):
        return _type_badge(obj.type)

    @admin.display(description="Currency", ordering="currency")
    def currency_display(self, obj):
        return _currency_badge(obj.currency)

    @admin.display(description="Currency")
    def currency_badge_detail(self, obj):
        return _currency_badge(obj.currency)

    @admin.display(description="Balance", ordering="balance")
    def balance_display(self, obj):
        return _balance_display(obj.balance, obj.blocked_balance, obj.loan_blocked_balance)

    @admin.display(description="Available Balance")
    def available_balance_display(self, obj):
        avail = obj.balance - obj.blocked_balance
        color = "#28a745" if avail > 0 else "#dc3545"
        return format_html(
            '<span style="font-weight:700;font-family:monospace;color:{}">{}</span>',
            color, avail,
        )

    @admin.display(description="Status", ordering="status")
    def status_display(self, obj):
        return _status_badge(obj.status)

    @admin.display(description="Status")
    def status_badge_detail(self, obj):
        return _status_badge(obj.status)

    @admin.display(description="Primary")
    def primary_icon(self, obj):
        return _bool_icon(obj.is_primary)

    @admin.display(description="Transactions")
    def transactions_link(self, obj):
        url = (
            reverse("admin:transactions_transaction_changelist")
            + f"?account__id__exact={obj.pk}"
        )
        count = obj.transactions.count()
        return format_html(
            '<a href="{}" style="font-weight:600">{} transaction(s) \u2192</a>',
            url, count,
        )
from decimal import Decimal

from django.contrib import admin, messages
from django.db.models import Count, Sum, Q
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import Loan, LoanRequest, LoanStatus, LoanRequestStatus, LoanType
from .services import LoanService

# ---------------------------------------------------------------------------
# Badge / colour helpers
# ---------------------------------------------------------------------------

REQUEST_STATUS_COLORS = {
    "PENDING":      "#fd7e14",
    "UNDER_REVIEW": "#17a2b8",
    "APPROVED":     "#28a745",
    "REJECTED":     "#dc3545",
}

LOAN_STATUS_COLORS = {
    "ACTIVE":    "#28a745",
    "COMPLETED": "#417690",
    "DEFAULTED": "#dc3545",
    "CLOSED":    "#6c757d",
}

LOAN_TYPE_COLORS = {
    "PERSONAL": "#417690",
    "HOME":     "#28a745",
    "CAR":      "#fd7e14",
    "BUSINESS": "#6f42c1",
}

RISK_THRESHOLDS = {
    "low":    (0,  30),
    "medium": (30, 60),
    "high":   (60, 101),
}


def _req_status_badge(status):
    color = REQUEST_STATUS_COLORS.get(status, "#999")
    return format_html(
        '<span style="background:{};color:#fff;padding:2px 10px;border-radius:12px;'
        'font-size:11px;font-weight:600;letter-spacing:.5px">{}</span>',
        color, status,
    )


def _loan_status_badge(status):
    color = LOAN_STATUS_COLORS.get(status, "#999")
    return format_html(
        '<span style="background:{};color:#fff;padding:2px 10px;border-radius:12px;'
        'font-size:11px;font-weight:600;letter-spacing:.5px">{}</span>',
        color, status,
    )


def _type_badge(loan_type):
    color = LOAN_TYPE_COLORS.get(loan_type, "#999")
    return format_html(
        '<span style="background:{};color:#fff;padding:2px 10px;border-radius:12px;'
        'font-size:11px;font-weight:600;letter-spacing:.5px">{}</span>',
        color, loan_type,
    )


def _risk_bar(score):
    if score >= 60:
        color = "#dc3545"
    elif score >= 30:
        color = "#fd7e14"
    else:
        color = "#28a745"
    return format_html(
        '<div style="display:flex;align-items:center;gap:8px">'
        '<div style="background:#eee;border-radius:4px;width:80px;height:10px;overflow:hidden">'
        '<div style="background:{};height:100%;width:{}%"></div></div>'
        '<span style="font-weight:600;color:{}">{}</span>'
        '</div>',
        color, min(score, 100), color, score,
    )


def _progress_bar(paid, total):
    """Repayment progress bar: paid / total_payable."""
    if not total or total == 0:
        pct = 0
    else:
        pct = min(int(paid / total * 100), 100)
    color = "#28a745" if pct >= 80 else "#417690" if pct >= 40 else "#fd7e14"
    return format_html(
        '<div style="display:flex;align-items:center;gap:8px">'
        '<div style="background:#eee;border-radius:4px;width:90px;height:10px;overflow:hidden">'
        '<div style="background:{};height:100%;width:{}%"></div></div>'
        '<span style="font-size:12px;font-weight:600;color:{}">{}%</span>'
        '</div>',
        color, pct, color, pct,
    )


# ---------------------------------------------------------------------------
# Bulk actions on LoanRequest
# ---------------------------------------------------------------------------

@admin.action(description="Evaluate risk score for selected requests")
def evaluate_requests(modeladmin, request, queryset):
    updated = 0
    for req in queryset.filter(status=LoanRequestStatus.PENDING):
        LoanService.evaluate_request(req)
        updated += 1
    messages.info(request, f"{updated} request(s) evaluated and moved to UNDER_REVIEW.")


@admin.action(description="Reject selected PENDING / UNDER_REVIEW requests")
def bulk_reject(modeladmin, request, queryset):
    allowed = queryset.filter(
        status__in=[LoanRequestStatus.PENDING, LoanRequestStatus.UNDER_REVIEW]
    )
    updated = 0
    for req in allowed:
        LoanService.reject_request(
            manager=request.user,
            req=req,
            reason="Bulk rejection by admin.",
        )
        updated += 1
    messages.warning(request, f"{updated} request(s) rejected.")


# ---------------------------------------------------------------------------
# Bulk actions on Loan
# ---------------------------------------------------------------------------

@admin.action(description="Mark selected loans as DEFAULTED")
def mark_defaulted(modeladmin, request, queryset):
    updated = queryset.filter(status=LoanStatus.ACTIVE).update(
        status=LoanStatus.DEFAULTED
    )
    messages.warning(request, f"{updated} loan(s) marked as DEFAULTED.")


@admin.action(description="Mark selected loans as CLOSED")
def mark_closed(modeladmin, request, queryset):
    updated = queryset.filter(
        status__in=[LoanStatus.COMPLETED, LoanStatus.DEFAULTED]
    ).update(status=LoanStatus.CLOSED)
    messages.info(request, f"{updated} loan(s) marked as CLOSED.")


# ---------------------------------------------------------------------------
# InstallmentInline (read-only inside Loan detail)
# ---------------------------------------------------------------------------

class InstallmentInline(admin.TabularInline):
    # Import here to avoid circular at module level
    from apps.installments.models import Installment as _Installment
    model = _Installment
    extra = 0
    can_delete = False
    show_change_link = False
    ordering = ("number",)
    fields = (
        "number", "due_date", "amount",
        "paid_amount", "penalty_amount",
        "status", "paid_at",
    )
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# ---------------------------------------------------------------------------
# LoanRequestAdmin
# ---------------------------------------------------------------------------

@admin.register(LoanRequest)
class LoanRequestAdmin(admin.ModelAdmin):
    change_list_template = "admin/loans/loanrequest_changelist.html"

    # ------------------------------------------------------------------
    # List view
    # ------------------------------------------------------------------
    list_display = (
        "short_id", "customer_link", "loan_type_display",
        "amount", "duration_months",
        "risk_bar_display", "status_display", "created_at",
    )
    list_filter = (
        "status", "loan_type",
        ("created_at", admin.DateFieldListFilter),
    )
    search_fields = (
        "customer__fullname", "customer__phone",
        "customer__national_code",
    )
    ordering      = ("-created_at",)
    list_per_page = 40
    date_hierarchy = "created_at"
    actions        = [evaluate_requests, bulk_reject]

    # ------------------------------------------------------------------
    # Detail / Add views
    # ------------------------------------------------------------------

    # CHANGE view — customer is locked (immutable financial record)
    readonly_fields = (
        "id", "customer", "created_at",
        "status_badge_detail", "type_badge_detail",
        "risk_bar_detail", "debt_ratio_display",
        "loan_link",
    )

    fieldsets = (
        ("Identity", {
            "fields": ("id", "customer", "created_at"),
        }),
        ("Request Details", {
            "fields": (
                "loan_type", "type_badge_detail",
                "amount", "duration_months",
            ),
        }),
        ("Financial Profile", {
            "fields": (
                "monthly_income", "existing_debt",
                "debt_ratio_display",
            ),
        }),
        ("Risk & Decision", {
            "fields": (
                "risk_score", "risk_bar_detail",
                "status", "status_badge_detail",
                "manager_note",
            ),
        }),
        ("Related Loan", {
            "fields": ("loan_link",),
        }),
    )

    # ADD view — customer is a searchable popup, all fields editable
    add_fieldsets = (
        ("Customer", {
            "description": (
                "Select the customer this loan request is being filed for. "
                "Click the magnifier icon to search by name or phone."
            ),
            "fields": ("customer",),
        }),
        ("Request Details", {
            "fields": (
                "loan_type",
                "amount",
                "duration_months",
            ),
        }),
        ("Financial Profile", {
            "fields": (
                "monthly_income",
                "existing_debt",
            ),
        }),
        ("Initial Decision", {
            "fields": (
                "status",
                "risk_score",
                "manager_note",
            ),
        }),
    )

    # raw_id_fields gives a search-popup for the User FK —
    # far better than a huge <select> with thousands of customers.
    raw_id_fields = ("customer",)

    def get_readonly_fields(self, request, obj=None):
        """
        ADD    (obj is None) -> customer is editable, only display helpers are readonly.
        CHANGE (obj exists)  -> customer is locked; request belongs to that person.
        """
        if obj is None:
            # on add: only the computed display helpers are readonly
            return (
                "status_badge_detail", "type_badge_detail",
                "risk_bar_detail", "debt_ratio_display",
                "loan_link",
            )
        return self.readonly_fields

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.add_fieldsets
        return self.fieldsets

    # ------------------------------------------------------------------
    # Approve / Reject custom URLs
    # ------------------------------------------------------------------

    def get_urls(self):
        urls = super().get_urls()
        extra = [
            path(
                "<uuid:pk>/approve/",
                self.admin_site.admin_view(self.approve_view),
                name="loans_loanrequest_approve",
            ),
            path(
                "<uuid:pk>/reject/",
                self.admin_site.admin_view(self.reject_view),
                name="loans_loanrequest_reject",
            ),
            path(
                "dashboard/",
                self.admin_site.admin_view(self.dashboard_view),
                name="loans_loanrequest_dashboard",
            ),
        ]
        return extra + urls

    def approve_view(self, request, pk):
        req = LoanRequest.objects.get(pk=pk)
        if req.status not in (
            LoanRequestStatus.PENDING,
            LoanRequestStatus.UNDER_REVIEW,
        ):
            messages.error(request, "Only PENDING or UNDER_REVIEW requests can be approved.")
            return redirect(reverse("admin:loans_loanrequest_change", args=[pk]))

        try:
            loan = LoanService.approve_request(manager=request.user, req=req)
            messages.success(
                request,
                f"Loan request approved. Loan #{str(loan.id)[:8]}… created."
            )
        except Exception as e:
            messages.error(request, f"Approval failed: {e}")

        return redirect(reverse("admin:loans_loanrequest_change", args=[pk]))

    def reject_view(self, request, pk):
        req = LoanRequest.objects.get(pk=pk)
        if request.method == "POST":
            reason = request.POST.get("reason", "").strip()
            if not reason:
                messages.error(request, "Rejection reason is required.")
            else:
                LoanService.reject_request(
                    manager=request.user, req=req, reason=reason
                )
                messages.warning(request, "Loan request rejected.")
                return redirect(reverse("admin:loans_loanrequest_change", args=[pk]))

        context = dict(
            self.admin_site.each_context(request),
            title="Reject Loan Request",
            req=req,
            back_url=reverse("admin:loans_loanrequest_change", args=[pk]),
        )
        return render(request, "admin/loans/loanrequest_reject.html", context)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        qs = LoanRequest.objects.all()

        extra_context["summary_cards"] = [
            {"label": "Total",        "value": qs.count(),                                          "color": "#333"},
            {"label": "Pending",      "value": qs.filter(status=LoanRequestStatus.PENDING).count(), "color": "#fd7e14"},
            {"label": "Under Review", "value": qs.filter(status=LoanRequestStatus.UNDER_REVIEW).count(), "color": "#17a2b8"},
            {"label": "Approved",     "value": qs.filter(status=LoanRequestStatus.APPROVED).count(), "color": "#28a745"},
            {"label": "Rejected",     "value": qs.filter(status=LoanRequestStatus.REJECTED).count(), "color": "#dc3545"},
        ]
        extra_context["dashboard_url"] = reverse("admin:loans_loanrequest_dashboard")
        return super().changelist_view(request, extra_context=extra_context)

    def dashboard_view(self, request):
        rqs = LoanRequest.objects.all()
        lqs = Loan.objects.all()

        # Request counts
        total_req    = rqs.count()
        pending      = rqs.filter(status=LoanRequestStatus.PENDING).count()
        under_review = rqs.filter(status=LoanRequestStatus.UNDER_REVIEW).count()
        approved     = rqs.filter(status=LoanRequestStatus.APPROVED).count()
        rejected     = rqs.filter(status=LoanRequestStatus.REJECTED).count()

        # Loan counts
        total_loans = lqs.count()
        active      = lqs.filter(status=LoanStatus.ACTIVE).count()
        completed   = lqs.filter(status=LoanStatus.COMPLETED).count()
        defaulted   = lqs.filter(status=LoanStatus.DEFAULTED).count()
        closed      = lqs.filter(status=LoanStatus.CLOSED).count()

        # Volumes
        total_principal = lqs.aggregate(v=Sum("principal_amount"))["v"] or Decimal("0")
        total_payable   = lqs.aggregate(v=Sum("total_payable"))["v"] or Decimal("0")
        total_paid      = lqs.aggregate(v=Sum("paid_amount"))["v"] or Decimal("0")
        total_remaining = total_payable - total_paid

        cards = [
            {"label": "Total Requests",  "value": total_req,                    "color": "#333",    "sub": "all time"},
            {"label": "Pending",         "value": pending,                      "color": "#fd7e14", "sub": "awaiting action"},
            {"label": "Under Review",    "value": under_review,                 "color": "#17a2b8", "sub": "being assessed"},
            {"label": "Approved",        "value": approved,                     "color": "#28a745", "sub": "converted to loan"},
            {"label": "Rejected",        "value": rejected,                     "color": "#dc3545", "sub": "declined"},
            {"label": "Active Loans",    "value": active,                       "color": "#28a745", "sub": "ongoing"},
            {"label": "Defaulted",       "value": defaulted,                    "color": "#dc3545", "sub": "missed payments"},
            {"label": "Total Principal", "value": f"{total_principal:,.2f}",    "color": "#417690", "sub": "disbursed"},
            {"label": "Outstanding",     "value": f"{total_remaining:,.2f}",    "color": "#fd7e14", "sub": "yet to collect"},
        ]

        # Request status bar chart
        req_status_data = {
            "PENDING":      (pending,      "#fd7e14"),
            "UNDER REVIEW": (under_review, "#17a2b8"),
            "APPROVED":     (approved,     "#28a745"),
            "REJECTED":     (rejected,     "#dc3545"),
        }
        max_r = max((v for v, _ in req_status_data.values()), default=1) or 1
        req_buckets = [
            {
                "label":  label,
                "count":  count,
                "height": max(int(count / max_r * 110), 4),
                "color":  color,
            }
            for label, (count, color) in req_status_data.items()
        ]

        # Loan status bar chart
        loan_status_data = {
            "ACTIVE":    (active,    "#28a745"),
            "COMPLETED": (completed, "#417690"),
            "DEFAULTED": (defaulted, "#dc3545"),
            "CLOSED":    (closed,    "#6c757d"),
        }
        max_l = max((v for v, _ in loan_status_data.values()), default=1) or 1
        loan_buckets = [
            {
                "label":  label,
                "count":  count,
                "height": max(int(count / max_l * 110), 4),
                "color":  color,
            }
            for label, (count, color) in loan_status_data.items()
        ]

        # Loan type breakdown
        type_rows = (
            rqs.values("loan_type")
               .annotate(count=Count("id"), volume=Sum("amount"))
               .order_by("-count")
        )
        max_t = type_rows[0]["count"] if type_rows else 1
        type_data = [
            {
                "type":   row["loan_type"],
                "count":  row["count"],
                "volume": row["volume"] or Decimal("0"),
                "width":  max(int(row["count"] / max_t * 100), 2),
                "color":  LOAN_TYPE_COLORS.get(row["loan_type"], "#999"),
            }
            for row in type_rows
        ]

        # Requests pending action (PENDING + UNDER_REVIEW) — last 10
        pending_reqs = (
            rqs.filter(status__in=[
                LoanRequestStatus.PENDING,
                LoanRequestStatus.UNDER_REVIEW,
            ])
            .select_related("customer")
            .order_by("created_at")[:10]
        )
        pending_data = [
            {
                "id":           str(r.id)[:8] + "…",
                "customer":     r.customer.fullname,
                "phone":        r.customer.phone,
                "loan_type":    r.loan_type,
                "t_color":      LOAN_TYPE_COLORS.get(r.loan_type, "#999"),
                "amount":       r.amount,
                "duration":     r.duration_months,
                "risk_score":   r.risk_score,
                "risk_color":   "#dc3545" if r.risk_score >= 60 else "#fd7e14" if r.risk_score >= 30 else "#28a745",
                "status":       r.status,
                "s_color":      REQUEST_STATUS_COLORS.get(r.status, "#999"),
                "created_at":   r.created_at,
                "change_url":   reverse("admin:loans_loanrequest_change", args=[r.pk]),
                "approve_url":  reverse("admin:loans_loanrequest_approve", args=[r.pk]),
                "reject_url":   reverse("admin:loans_loanrequest_reject", args=[r.pk]),
            }
            for r in pending_reqs
        ]

        # Defaulted loans — last 10
        defaulted_loans = (
            lqs.filter(status=LoanStatus.DEFAULTED)
               .select_related("customer")
               .order_by("-started_at")[:10]
        )
        defaulted_data = [
            {
                "id":         str(l.id)[:8] + "…",
                "customer":   l.customer.fullname,
                "phone":      l.customer.phone,
                "principal":  l.principal_amount,
                "paid":       l.paid_amount,
                "remaining":  l.total_payable - l.paid_amount,
                "change_url": reverse("admin:loans_loan_change", args=[l.pk]),
            }
            for l in defaulted_loans
        ]

        context = dict(
            self.admin_site.each_context(request),
            title="Loans Dashboard",
            cards=cards,
            req_buckets=req_buckets,
            loan_buckets=loan_buckets,
            type_data=type_data,
            pending_data=pending_data,
            defaulted_data=defaulted_data,
        )
        return render(request, "admin/loans/loan_dashboard.html", context)

    # ------------------------------------------------------------------
    # Custom display columns
    # ------------------------------------------------------------------

    @admin.display(description="ID")
    def short_id(self, obj):
        return str(obj.id)[:8] + "\u2026"

    @admin.display(description="Customer", ordering="customer__fullname")
    def customer_link(self, obj):
        url = reverse("admin:users_user_change", args=[obj.customer_id])
        return format_html(
            '<a href="{}" style="font-weight:600">{}</a>'
            '<br><span style="font-size:11px;color:#aaa">{}</span>',
            url, obj.customer.fullname, obj.customer.phone,
        )

    @admin.display(description="Type", ordering="loan_type")
    def loan_type_display(self, obj):
        return _type_badge(obj.loan_type)

    @admin.display(description="Type")
    def type_badge_detail(self, obj):
        return _type_badge(obj.loan_type)

    @admin.display(description="Risk Score", ordering="risk_score")
    def risk_bar_display(self, obj):
        return _risk_bar(obj.risk_score)

    @admin.display(description="Risk Score")
    def risk_bar_detail(self, obj):
        return _risk_bar(obj.risk_score)

    @admin.display(description="Status", ordering="status")
    def status_display(self, obj):
        return _req_status_badge(obj.status)

    @admin.display(description="Status")
    def status_badge_detail(self, obj):
        return _req_status_badge(obj.status)

    @admin.display(description="Debt Ratio")
    def debt_ratio_display(self, obj):
        if not obj.monthly_income:
            return mark_safe('<span style="color:#aaa">\u2014</span>')
        ratio = obj.existing_debt / obj.monthly_income
        color = "#dc3545" if ratio > Decimal("0.5") else "#28a745"
        return format_html(
            '<span style="font-weight:700;color:{}">{:.2f}</span>'
            '<span style="font-size:11px;color:#aaa"> '
            '(debt / income)</span>',
            color, ratio,
        )

    @admin.display(description="Resulting Loan")
    def loan_link(self, obj):
        try:
            loan = obj.loan
            url = reverse("admin:loans_loan_change", args=[loan.pk])
            return format_html(
                '<a href="{}" style="font-weight:600">Loan #{}</a>',
                url, str(loan.id)[:8] + "\u2026",
            )
        except Exception:
            return mark_safe(
                '<span style="color:#aaa;font-style:italic">No loan yet</span>'
            )

    # ------------------------------------------------------------------
    # Inject approve / reject buttons into the change form
    # ------------------------------------------------------------------

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        try:
            req = LoanRequest.objects.get(pk=object_id)
            if req.status in (
                LoanRequestStatus.PENDING,
                LoanRequestStatus.UNDER_REVIEW,
            ):
                extra_context["approve_url"] = reverse(
                    "admin:loans_loanrequest_approve", args=[object_id]
                )
                extra_context["reject_url"] = reverse(
                    "admin:loans_loanrequest_reject", args=[object_id]
                )
        except LoanRequest.DoesNotExist:
            pass
        return super().change_view(
            request, object_id, form_url, extra_context=extra_context
        )


# ---------------------------------------------------------------------------
# LoanAdmin
# ---------------------------------------------------------------------------

@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):

    # ------------------------------------------------------------------
    # List view
    # ------------------------------------------------------------------
    list_display = (
        "short_id", "customer_link", "loan_type_display",
        "principal_amount", "progress_display",
        "status_display", "duration_months", "started_at",
    )
    list_filter = (
        "status", "loan_request__loan_type",
        ("started_at", admin.DateFieldListFilter),
    )
    search_fields = (
        "customer__fullname", "customer__phone",
        "customer__national_code",
    )
    ordering       = ("-started_at",)
    list_per_page  = 40
    date_hierarchy = "started_at"
    actions        = [mark_defaulted, mark_closed]
    inlines        = [InstallmentInline]

    # ------------------------------------------------------------------
    # Detail view
    # ------------------------------------------------------------------
    readonly_fields = (
        "id", "customer", "loan_request_link", "started_at",
        "status_badge_detail", "type_badge_detail",
        "progress_bar_detail", "remaining_amount",
        "interest_rate", "total_payable", "monthly_installment",
    )

    fieldsets = (
        ("Identity", {
            "fields": ("id", "customer", "loan_request_link", "started_at"),
        }),
        ("Loan Terms", {
            "fields": (
                "loan_request__loan_type" if False else "type_badge_detail",
                "principal_amount", "interest_rate",
                "duration_months", "monthly_installment",
                "total_payable",
            ),
        }),
        ("Repayment", {
            "fields": (
                "paid_amount", "remaining_amount",
                "progress_bar_detail",
            ),
        }),
        ("Status", {
            "fields": ("status", "status_badge_detail"),
        }),
    )

    # Loans are created only via LoanService.approve_request
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    # ------------------------------------------------------------------
    # Custom display columns
    # ------------------------------------------------------------------

    @admin.display(description="ID")
    def short_id(self, obj):
        return str(obj.id)[:8] + "\u2026"

    @admin.display(description="Customer", ordering="customer__fullname")
    def customer_link(self, obj):
        url = reverse("admin:users_user_change", args=[obj.customer_id])
        return format_html(
            '<a href="{}" style="font-weight:600">{}</a>'
            '<br><span style="font-size:11px;color:#aaa">{}</span>',
            url, obj.customer.fullname, obj.customer.phone,
        )

    @admin.display(description="Type", ordering="loan_request__loan_type")
    def loan_type_display(self, obj):
        return _type_badge(obj.loan_request.loan_type)

    @admin.display(description="Type")
    def type_badge_detail(self, obj):
        return _type_badge(obj.loan_request.loan_type)

    @admin.display(description="Status", ordering="status")
    def status_display(self, obj):
        return _loan_status_badge(obj.status)

    @admin.display(description="Status")
    def status_badge_detail(self, obj):
        return _loan_status_badge(obj.status)

    @admin.display(description="Repayment Progress", ordering="paid_amount")
    def progress_display(self, obj):
        return _progress_bar(obj.paid_amount, obj.total_payable)

    @admin.display(description="Repayment Progress")
    def progress_bar_detail(self, obj):
        return _progress_bar(obj.paid_amount, obj.total_payable)

    @admin.display(description="Remaining")
    def remaining_amount(self, obj):
        remaining = obj.total_payable - obj.paid_amount
        color = "#dc3545" if remaining > 0 else "#28a745"
        return format_html(
            '<span style="font-weight:700;font-family:monospace;color:{}">{}</span>',
            color, remaining,
        )

    @admin.display(description="Loan Request")
    def loan_request_link(self, obj):
        url = reverse("admin:loans_loanrequest_change", args=[obj.loan_request_id])
        return format_html(
            '<a href="{}">Request #{}</a>',
            url, str(obj.loan_request_id)[:8] + "\u2026",
        )
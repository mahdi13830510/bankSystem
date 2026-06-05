import os
import joblib
import numpy as np
from django.contrib import admin, messages
from django.db.models import Count, Avg, Q
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import FraudReport, FraudDecision
from .services.ml_scoring import MLScoringService
from .services.rules import FraudRules

ARTIFACT_PATH = os.path.join(os.path.dirname(__file__), "ml", "fraud_artifact.pkl")

FEATURE_NAMES = ["amount", "hour_of_day", "is_weekend", "is_interbank",
                 "history_count", "fee_ratio", "txn_type_encoded"]

DECISION_COLORS = {
    "SAFE": "#28a745",
    "SUSPICIOUS": "#fd7e14",
    "BLOCKED": "#dc3545",
}

# ---------------------------------------------------------------------------
# Inline score badge helper
# ---------------------------------------------------------------------------
def _score_bar(score):
    if score is None:
        score = 0

    if score >= 80:
        color = "#dc3545"
    elif score >= 50:
        color = "#fd7e14"
    else:
        color = "#28a745"

    pct = min(score, 100)

    return format_html(
        '<div style="display:flex;align-items:center;gap:8px">'
        '<div style="background:#eee;border-radius:4px;width:80px;height:10px;overflow:hidden">'
        '<div style="background:{};height:100%;width:{}%"></div></div>'
        '<span style="font-weight:600;color:{}">{}</span></div>',
        color, pct, color, score,
    )


def _decision_badge(decision):
    color = DECISION_COLORS.get(decision, "#999")
    return format_html(
        '<span style="background:{};color:#fff;padding:2px 10px;border-radius:12px;'
        'font-size:11px;font-weight:600;letter-spacing:.5px">{}</span>',
        color, decision,
    )


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

@admin.action(description="Override decision to SAFE")
def mark_safe_action(modeladmin, request, queryset):
    updated = queryset.update(decision=FraudDecision.SAFE)
    messages.success(request, f"{updated} report(s) overridden to SAFE.")


@admin.action(description="Override decision to BLOCKED")
def mark_blocked_action(modeladmin, request, queryset):
    updated = queryset.update(decision=FraudDecision.BLOCKED)
    messages.warning(request, f"{updated} report(s) overridden to BLOCKED.")


@admin.action(description="Re-score selected reports with current ML model")
def rescore_action(modeladmin, request, queryset):
    updated = 0
    for report in queryset:
        reason = report.reason or {}
        features = {
            "amount": float(reason.get("amount", 0)),
            "hour_of_day": float(reason.get("hour_of_day", 12)),
            "is_weekend": float(reason.get("is_weekend", 0)),
            "is_interbank": float(reason.get("is_interbank", 0)),
            "history_count": float(reason.get("history", 0)),
            "fee_ratio": float(reason.get("fee_ratio", 0.01)),
            "txn_type_encoded": float(reason.get("txn_type_encoded", 0)),
        }
        new_score = MLScoringService.predict(features)
        new_decision = FraudRules.decide(new_score)
        report.score = new_score
        report.decision = new_decision
        report.save(update_fields=["score", "decision"])
        updated += 1
    messages.success(request, f"{updated} report(s) re-scored.")


# ---------------------------------------------------------------------------
# Main admin class
# ---------------------------------------------------------------------------

@admin.register(FraudReport)
class FraudReportAdmin(admin.ModelAdmin):
    change_list_template = "admin/fraud/fraudreport_changelist.html"

    list_display = (
        "short_id", "transaction_id", "user_id",
        "score_display", "decision_display", "reason_summary", "created_at",
    )
    list_filter = ("decision", ("created_at", admin.DateFieldListFilter))
    search_fields = ("transaction_id", "user_id")
    ordering = ("-created_at",)
    readonly_fields = (
        "id", "transaction_id", "user_id", "score_bar_detail",
        "decision_display", "reason_pretty", "created_at",
    )
    actions = [mark_safe_action, mark_blocked_action, rescore_action]
    list_per_page = 50

    fieldsets = (
        ("Identity", {
            "fields": ("id", "transaction_id", "user_id", "created_at"),
        }),
        ("Risk Assessment", {
            "fields": ("score_bar_detail", "decision_display"),
        }),
        ("Details", {
            "fields": ("reason_pretty",),
        }),
    )

    # ------------------------------------------------------------------
    # Custom display columns
    # ------------------------------------------------------------------

    @admin.display(description="ID")
    def short_id(self, obj):
        return str(obj.id)[:8] + "..."

    @admin.display(description="Score", ordering="score")
    def score_display(self, obj):
        return _score_bar(obj.score)

    @admin.display(description="Decision", ordering="decision")
    def decision_display(self, obj):
        return _decision_badge(obj.decision)

    @admin.display(description="Score")
    def score_bar_detail(self, obj):
        return _score_bar(obj.score)

    @admin.display(description="Reason")
    def reason_summary(self, obj):
        r = obj.reason or {}
        amt = r.get("amount", "-")
        return f"amount={amt}"

    @admin.display(description="Reason (full)")
    def reason_pretty(self, obj):
        import json
        return mark_safe(
            '<pre style="background:#f8f8f8;padding:12px;border-radius:4px;'
            'font-size:12px;white-space:pre-wrap;word-break:break-all">'
            + json.dumps(obj.reason, indent=2, default=str)
            + "</pre>"
        )

    # ------------------------------------------------------------------
    # Extra admin views: model dashboard + score tester
    # ------------------------------------------------------------------

    def get_urls(self):
        urls = super().get_urls()
        extra = [
            path(
                "model-dashboard/",
                self.admin_site.admin_view(self.model_dashboard_view),
                name="fraud_model_dashboard",
            ),
            path(
                "score-test/",
                self.admin_site.admin_view(self.score_test_view),
                name="fraud_score_test",
            ),
        ]
        return extra + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        qs = FraudReport.objects.all()
        total = qs.count()
        blocked = qs.filter(decision=FraudDecision.BLOCKED).count()
        suspicious = qs.filter(decision=FraudDecision.SUSPICIOUS).count()
        avg_score = qs.aggregate(a=Avg("score"))["a"] or 0
        extra_context["summary_cards"] = [
            {"label": "Total Reports", "value": total, "color": "#333"},
            {"label": "Blocked", "value": blocked, "color": "#dc3545"},
            {"label": "Suspicious", "value": suspicious, "color": "#fd7e14"},
            {"label": "Avg Score", "value": f"{avg_score:.1f}", "color": "#417690"},
        ]
        extra_context["model_dashboard_url"] = reverse("admin:fraud_model_dashboard")
        return super().changelist_view(request, extra_context=extra_context)

    def model_dashboard_view(self, request):
        # -- model info --
        model_params = {"status": "not loaded"}
        scaler_stats = []
        if os.path.exists(ARTIFACT_PATH):
            artifact = joblib.load(ARTIFACT_PATH)
            m = artifact["model"]
            sc = artifact["scaler"]
            model_params = {
                "Algorithm": "IsolationForest",
                "n_estimators": m.n_estimators,
                "contamination": m.contamination,
                "n_features": m.n_features_in_,
                "score_low (safe)": f"{artifact['score_low']:.6f}",
                "score_high (fraud)": f"{artifact['score_high']:.6f}",
                "artifact_path": ARTIFACT_PATH,
            }
            for name, mean, std in zip(FEATURE_NAMES, sc.mean_, sc.scale_):
                scaler_stats.append({
                    "name": name,
                    "mean": f"{mean:.4f}",
                    "std": f"{std:.4f}",
                })

        # -- score distribution --
        reports = FraudReport.objects.order_by("-created_at")[:500]
        buckets_raw = [0] * 10
        for r in reports:
            idx = min(r.score // 10, 9)
            buckets_raw[idx] += 1
        max_count = max(buckets_raw) or 1
        score_buckets = []
        for i, count in enumerate(buckets_raw):
            lo, hi = i * 10, i * 10 + 9
            score_buckets.append({
                "label": f"{lo}-{hi}",
                "count": count,
                "height": max(int(count / max_count * 110), 2),
                "color": "#dc3545" if lo >= 80 else "#fd7e14" if lo >= 50 else "#28a745",
            })

        # -- summary cards --
        qs = FraudReport.objects.all()
        avg = qs.aggregate(a=Avg("score"))["a"] or 0
        cards = [
            {"label": "Total Reports", "value": qs.count(), "color": "#333", "sub": ""},
            {"label": "Blocked", "value": qs.filter(decision="BLOCKED").count(), "color": "#dc3545",
             "sub": "score >= 80"},
            {"label": "Suspicious", "value": qs.filter(decision="SUSPICIOUS").count(), "color": "#fd7e14",
             "sub": "score 50-79"},
            {"label": "Safe", "value": qs.filter(decision="SAFE").count(), "color": "#28a745", "sub": "score < 50"},
            {"label": "Avg Score", "value": f"{avg:.1f}", "color": "#417690", "sub": "last all time"},
            {"label": "Model File", "value": "Loaded" if os.path.exists(ARTIFACT_PATH) else "Missing",
             "color": "#28a745" if os.path.exists(ARTIFACT_PATH) else "#dc3545", "sub": ""},
        ]

        # -- test form fields --
        test_fields = [
            {"name": "amount", "label": "Amount", "type": "number", "default": "500", "step": "0.01"},
            {"name": "hour_of_day", "label": "Hour (0-23)", "type": "number", "default": "14", "step": "1"},
            {"name": "is_weekend", "label": "Weekend (0/1)", "type": "number", "default": "0", "step": "1"},
            {"name": "is_interbank", "label": "Interbank (0/1)", "type": "number", "default": "0", "step": "1"},
            {"name": "history_count", "label": "History Count", "type": "number", "default": "10", "step": "1"},
            {"name": "fee_ratio", "label": "Fee Ratio", "type": "number", "default": "0.01", "step": "0.001"},
            {"name": "txn_type_encoded", "label": "Txn Type (0-9)", "type": "number", "default": "0", "step": "1"},
        ]

        # -- test result from query param --
        test_result = request.session.pop("fraud_test_result", None)

        context = dict(
            self.admin_site.each_context(request),
            title="Fraud ML Model Dashboard",
            cards=cards,
            model_params=model_params,
            scaler_stats=scaler_stats,
            score_buckets=score_buckets,
            test_fields=test_fields,
            test_result=test_result,
        )
        return render(request, "admin/fraud/model_dashboard.html", context)

    def score_test_view(self, request):
        if request.method == "POST":
            try:
                features = {
                    "amount": float(request.POST.get("amount", 500)),
                    "hour_of_day": float(request.POST.get("hour_of_day", 12)),
                    "is_weekend": float(request.POST.get("is_weekend", 0)),
                    "is_interbank": float(request.POST.get("is_interbank", 0)),
                    "history_count": float(request.POST.get("history_count", 10)),
                    "fee_ratio": float(request.POST.get("fee_ratio", 0.01)),
                    "txn_type_encoded": float(request.POST.get("txn_type_encoded", 0)),
                }
                ml_score = MLScoringService.predict(features)

                # rule boosts (mirror risk_engine logic)
                rule_boost = 0
                if features["amount"] > 10000:
                    rule_boost += 20
                elif features["amount"] > 5000:
                    rule_boost += 10
                if features["history_count"] < 3:
                    rule_boost += 15
                if features["hour_of_day"] < 5 or features["hour_of_day"] >= 23:
                    rule_boost += 15
                if features["is_interbank"]:
                    rule_boost += 5

                combined_score = min(int(ml_score * 0.7 + rule_boost * 0.3), 100)
                decision = FraudRules.decide(combined_score)
                color = DECISION_COLORS.get(decision, "#999")

                request.session["fraud_test_result"] = {
                    "ml_score": ml_score,
                    "combined_score": combined_score,
                    "decision": decision,
                    "color": color,
                }
            except (ValueError, TypeError) as e:
                messages.error(request, f"Invalid input: {e}")
        return HttpResponseRedirect(reverse("admin:fraud_model_dashboard"))

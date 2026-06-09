from django.conf import settings
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import RedirectView
from django.views.static import serve

urlpatterns = [
    # ── Django admin ────────────────────────────────────────────────────────
    path('admin/', admin.site.urls),

    # ── Root → frontend entry point ─────────────────────────────────────────
    path('', RedirectView.as_view(url='/fe/auth/auth.html', permanent=False)),

    # ── Auth & Users ─────────────────────────────────────────────────────────
    path("api/v1/users/", include("apps.users.urls")),
    path("api/v1/auth/", include("apps.authentication.urls")),

    # ── Core banking ─────────────────────────────────────────────────────────
    path("accounts/", include("apps.accounts.urls")),
    path("api/transactions/", include("apps.transactions.urls")),
    path("loans/", include("apps.loans.urls")),
    path("installments/", include("apps.installments.urls")),

    # ── Operations ───────────────────────────────────────────────────────────
    path("notifications/", include("apps.notifications.urls")),
    path("fraud/", include("apps.fraud.urls")),
    path("auditlogs/", include("apps.auditlogs.urls")),
    path("dashboard/", include("apps.dashboard.urls")),

    # ── Banks ────────────────────────────────────────────────────────────────
    path("banks/", include("apps.banks.urls")),

    # ── AI agent ─────────────────────────────────────────────────────────────
    path("api/ai/", include("apps.ai_agent.urls")),

    # ── Frontend static files (works in both dev and prod) ────────────────────
    re_path(r'^fe/(?P<path>.*)$', serve, {'document_root': settings.BASE_DIR / 'Front-end'}),
]

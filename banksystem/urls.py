from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/v1/users/", include("apps.users.urls")),
    path("api/v1/auth/", include("apps.authentication.urls")),
    path('fraud/', include('apps.fraud.urls')),
    path("api/transactions/", include("apps.transactions.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("accounts/", include("apps.accounts.urls"))

]

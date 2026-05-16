from django.urls import path
from .views import DashboardView

app_name = "dashboard"

urlpatterns = [
    path("overview/", DashboardView.as_view(), name="dashboard-overview"),
]
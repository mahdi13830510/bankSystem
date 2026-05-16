from django.urls import path

from .views import FraudReportListView

urlpatterns = [
    path('reports/', FraudReportListView.as_view(), name='fraud-reports'),
]
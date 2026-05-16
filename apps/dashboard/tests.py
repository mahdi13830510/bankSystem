from django.test import TestCase
from unittest.mock import patch, MagicMock
from django.utils import timezone
from apps.dashboard.services.analytics_service import AnalyticsService
from apps.dashboard.services.fraud_service import FraudDashboardService
from apps.dashboard.services.kpi_service import KPIService
from apps.dashboard.services.realtime_service import RealtimeService
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()


class TestDashboardServices(TestCase):

    # ---  AnalyticsService ---
    @patch('apps.transactions.models.Transaction.objects.filter')
    def test_daily_trend(self, mock_filter):
        mock_agg = MagicMock()
        mock_agg.aggregate.return_value = {"amount__sum": 1000}
        mock_filter.return_value = mock_agg

        result = AnalyticsService.daily_trend(days=5)

        self.assertEqual(len(result), 5)
        self.assertEqual(result[-1]['volume'], 1000)
        args, kwargs = mock_filter.call_args
        self.assertIn('created_at__date', kwargs)

    # ---  FraudDashboardService ---
    @patch('apps.fraud.models.FraudReport.objects')
    def test_fraud_summary(self, mock_objects):
        mock_objects.count.return_value = 10
        mock_objects.filter.return_value.count.side_effect = [3, 4, 2]  # به ترتیب فراخوانی در کد

        summary = FraudDashboardService.fraud_summary()

        self.assertEqual(summary['total_alerts'], 10)
        self.assertEqual(summary['high_risk'], 3)
        self.assertEqual(summary['medium_risk'], 4)
        self.assertEqual(summary['resolved'], 2)

    @patch('apps.dashboard.services.fraud_service.FraudReport.objects.order_by')
    def test_recent_alerts(self, mock_order_by):
        mock_values = MagicMock()
        mock_values.values.return_value = [{"id": 1, "reason": "Suspicious"}]
        mock_order_by.return_value.__getitem__.return_value = mock_values

        mock_order_by.return_value[:10].values.return_value = [{"id": 1}]

        alerts = FraudDashboardService.recent_alerts(limit=10)
        self.assertIsInstance(alerts, list)
        self.assertTrue(len(alerts) >= 0)

    # ---  KPIService ---
    @patch('apps.accounts.models.Account.objects.aggregate')
    def test_financial_kpis(self, mock_aggregate):
        mock_aggregate.return_value = {"balance__sum": 5000, "balance__avg": 2500}

        res = KPIService.financial()
        self.assertEqual(res['total_balance'], 5000)
        self.assertEqual(res['avg_balance'], 2500)

    @patch('apps.users.models.User.objects')
    def test_users_kpis(self, mock_user_objects):
        mock_user_objects.count.return_value = 100
        mock_user_objects.filter.return_value.count.return_value = 90

        res = KPIService.users()
        self.assertEqual(res['total_users'], 100)
        self.assertEqual(res['active_users'], 90)

    # ---  RealtimeService ---
    @patch('apps.transactions.models.Transaction.objects.filter')
    @patch('apps.dashboard.services.realtime_service.now')
    def test_realtime_live(self, mock_now, mock_filter):
        fixed_now = timezone.now()
        mock_now.return_value = fixed_now
        mock_filter.return_value.count.return_value = 5

        res = RealtimeService.live()

        self.assertEqual(res['tx_last_minute'], 5)
        self.assertEqual(res['system_status'], "HEALTHY")
        mock_filter.assert_called_once_with(created_at__gte=fixed_now)


class TestDashboardView(APITestCase):

    def setUp(self):
        self.url = reverse("dashboard:dashboard-overview")
        self.admin_user = User.objects.create_superuser(email="test@gmail.com",phone="091345660949", password="123")

    def test_dashboard_permission_denied(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('apps.dashboard.views.KPIService')
    @patch('apps.dashboard.views.AnalyticsService')
    @patch('apps.dashboard.views.FraudDashboardService')
    @patch('apps.dashboard.views.RealtimeService')
    def test_dashboard_api_success(self, mock_realtime, mock_fraud, mock_analytics, mock_kpi):

        mock_kpi.financial.return_value = {"total_balance": 100}
        mock_kpi.users.return_value = {"total_users": 10}
        mock_kpi.loans.return_value = {"active_loans": 2}
        mock_kpi.transactions.return_value = {"total": 50}

        mock_analytics.daily_trend.return_value = [{"date": "2023", "volume": 100}]

        mock_fraud.fraud_summary.return_value = {"total_alerts": 5}
        mock_fraud.recent_alerts.return_value = []

        mock_realtime.live.return_value = {"system_status": "HEALTHY"}

        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertIn("kpis", response.data)
        self.assertIn("analytics", response.data)
        self.assertEqual(response.data["kpis"]["financial"]["total_balance"], 100)
        self.assertEqual(response.data["realtime"]["system_status"], "HEALTHY")

        mock_kpi.financial.assert_called_once()
        mock_analytics.daily_trend.assert_called_once()
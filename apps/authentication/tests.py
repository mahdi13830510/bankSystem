from django.test import TestCase

from rest_framework.test import APIClient

from apps.users.models import User
from apps.authentication.models import OTPCode, Session
from apps.authentication.services import AuthService


class AuthenticationViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            phone="09120000000",
            email="test@test.com",
            password="123456",
            fullname="Nima",
            national_code="1234567890",
            status="active"
        )

    def test_login_success(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {
                "phone": "09120000000",
                "password": "123456"
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "OTP sent")

        self.assertTrue(
            OTPCode.objects.filter(user=self.user).exists()
        )

    def test_login_wrong_password(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {
                "phone": "09120000000",
                "password": "wrongpass"
            }
        )

        self.assertNotEqual(response.status_code, 200)

    def test_verify_otp_success(self):
        otp = OTPCode.objects.create(
            user=self.user,
            code="123456",
            expires_at="2099-01-01T00:00:00Z"
        )

        response = self.client.post(
            "/api/v1/auth/verify-otp/",
            {
                "phone": "09120000000",
                "code": "123456"
            }, HTTP_USER_AGENT='Mozilla/5.0 (Windows NT 10.0; Win64; x64)'

        )

        self.assertEqual(response.status_code, 200)

        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)

        self.assertTrue(
            Session.objects.filter(user=self.user).exists()
        )

    def test_verify_otp_invalid(self):
        response = self.client.post(
            "/api/v1/auth/verify-otp/",
            {
                "phone": "09120000000",
                "code": "999999"
            }
        )

        self.assertNotEqual(response.status_code, 200)

    def test_logout_success(self):
        session = Session.objects.create(
            user=self.user,
            access_token="aaa",
            refresh_token="bbb",
            device_name="Chrome",
            ip_address="127.0.0.1",
            expires_at="2099-01-01T00:00:00Z"
        )

        response = self.client.post(
            "/api/v1/auth/logout/",
            {
                "refresh_token": "bbb"
            }
        )

        session.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(session.status, "revoked")


# services tests


class AuthServiceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            phone="09121111111",
            email="a@test.com",
            password="123456",
            fullname="Ali",
            national_code="9876543210",
            status="active"
        )

    def test_login_service_success(self):
        user = AuthService.login(
            "09121111111",
            "123456",
            "127.0.0.1",
            "Chrome"
        )

        self.assertEqual(user.id, self.user.id)

    def test_login_wrong_password(self):
        with self.assertRaises(Exception):
            AuthService.login(
                "09121111111",
                "wrong",
                "127.0.0.1",
                "Chrome"
            )


# test models


class SessionModelTests(TestCase):

    def test_create_session(self):
        user = User.objects.create_user(
            phone="09125555555",
            email="b@test.com",
            password="123456",
            fullname="Sara",
            national_code="1122334455",
            status="active"
        )

        session = Session.objects.create(
            user=user,
            access_token="aaa",
            refresh_token="bbb",
            device_name="Firefox",
            ip_address="127.0.0.1",
            expires_at="2099-01-01T00:00:00Z"
        )

        self.assertEqual(session.status, "active")

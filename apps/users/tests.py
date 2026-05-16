from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from rest_framework.test import APIClient

from apps.users.serializers import (
    RegisterSerializer,
    UserDetailSerializer,
    ProfileSerializer,
)
from apps.users.services import UserService
from apps.users.models import UserProfile

User = get_user_model()


# Manager tests
class UserManagerTests(TestCase):

    def test_create_user_requires_phone(self):
        with self.assertRaises(ValueError) as ctx:
            User.objects.create_user(
                phone="",
                email="a@test.com",
                password="pass1234",
                fullname="Ali",
                national_code="1234567890",
            )
        self.assertIn("Phone", str(ctx.exception))

    def test_create_user_requires_email(self):
        with self.assertRaises(ValueError) as ctx:
            User.objects.create_user(
                phone="09120000000",
                email="",
                password="pass1234",
                fullname="Ali",
                national_code="1234567890",
            )
        self.assertIn("Email", str(ctx.exception))

    def test_create_user_normalizes_email_and_sets_password(self):
        u = User.objects.create_user(
            phone="09120000001",
            email="A@Test.COM",
            password="pass1234",
            fullname="Ali",
            national_code="1234567890",
        )
        self.assertEqual(u.email, "A@test.com")
        self.assertTrue(u.check_password("pass1234"))

    def test_create_superuser_sets_defaults(self):
        su = User.objects.create_superuser(
            phone="09120000002",
            email="admin@test.com",
            password="pass1234",
            fullname="Admin",
            national_code="0987654321",
        )
        self.assertTrue(su.is_staff)
        self.assertTrue(su.is_superuser)
        if hasattr(su, "primary_role"):
            self.assertEqual(su.primary_role, "admin")
        if hasattr(su, "status"):
            self.assertEqual(su.status, "active")
        if hasattr(su, "is_verified"):
            self.assertTrue(su.is_verified)


# Model property is_blocked
class UserModelBlockedTests(TestCase):

    def test_is_blocked_true_when_blocked_until_in_future(self):
        u = User.objects.create_user(
            phone="09120000003",
            email="x1@test.com",
            password="pass1234",
            fullname="User1",
            national_code="1111111111",
        )
        u.blocked_until = timezone.now() + timezone.timedelta(hours=2)
        u.save()
        self.assertTrue(u.is_blocked)

    def test_is_blocked_false_when_blocked_until_in_past(self):
        u = User.objects.create_user(
            phone="09120000004",
            email="x2@test.com",
            password="pass1234",
            fullname="User2",
            national_code="2222222222",
        )
        u.blocked_until = timezone.now() - timezone.timedelta(hours=2)
        u.save()
        self.assertFalse(u.is_blocked)


# Service tests
class UserServiceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            phone="09120000010",
            email="u@test.com",
            password="oldpass123",
            fullname="Test User",
            national_code="3333333333",
        )

    def test_register_user_creates_user(self):
        data = {
            "phone": "09120000011",
            "email": "new@test.com",
            "password": "pass1234",
            "fullname": "New User",
            "national_code": "4444444444",
        }

        u = UserService.register_user(data)

        self.assertEqual(u.phone, data["phone"])
        self.assertEqual(u.email, data["email"])
        self.assertTrue(u.check_password(data["password"]))

    def test_block_user_sets_status_blocked(self):
        UserService.block_user(self.user)
        self.user.refresh_from_db()

        if hasattr(self.user, "status"):
            self.assertEqual(self.user.status, "blocked")

    def test_verify_user_sets_active_and_verified(self):
        UserService.verify_user(self.user)
        self.user.refresh_from_db()

        if hasattr(self.user, "is_verified"):
            self.assertTrue(self.user.is_verified)
        if hasattr(self.user, "status"):
            self.assertEqual(self.user.status, "active")

    def test_change_password_updates_hash(self):
        UserService.change_password(self.user, "newpass456")
        self.user.refresh_from_db()

        self.assertTrue(self.user.check_password("newpass456"))
        self.assertFalse(self.user.check_password("oldpass123"))


# Serializer tests
class RegisterSerializerTests(TestCase):

    def test_register_serializer_valid_data(self):
        data = {
            "phone": "09120000030",
            "email": "ser@test.com",
            "password": "pass1234",
            "fullname": "Serializer User",
            "national_code": "8888888888",
        }
        serializer = RegisterSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_register_serializer_missing_email_invalid(self):
        data = {
            "phone": "09120000031",
            "password": "pass1234",
            "fullname": "Serializer User",
            "national_code": "8888888888",
        }
        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_register_serializer_missing_phone_invalid(self):
        data = {
            "phone": "",
            "email": "ser2@test.com",
            "password": "pass1234",
            "fullname": "Serializer User",
            "national_code": "8888888889",
        }
        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("phone", serializer.errors)

    def test_register_serializer_missing_password_invalid(self):
        data = {
            "phone": "09120000032",
            "email": "ser2@test.com",
            "fullname": "Serializer User",
            "national_code": "8888888890",
        }
        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)


class UserDetailSerializerTests(TestCase):

    def test_user_detail_serializer_excludes_password(self):
        u = User.objects.create_user(
            phone="09120000040",
            email="detail@test.com",
            password="pass1234",
            fullname="Detail User",
            national_code="9999999999",
        )
        data = UserDetailSerializer(u).data
        self.assertNotIn("password", data)


class ProfileSerializerTests(TestCase):

    def test_profile_serializer_returns_data(self):
        u = User.objects.create_user(
            phone="09120000050",
            email="profile@test.com",
            password="pass1234",
            fullname="Profile User",
            national_code="1010101010",
        )
        profile = UserProfile.objects.create(user=u)

        data = ProfileSerializer(profile).data
        self.assertIsNotNone(data)
        self.assertIn("id", data if "id" in data else data.keys())


# API tests for RegisterView
class RegisterApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/users/register/"

    def test_register_success(self):
        payload = {
            "phone": "09120000060",
            "email": "api@test.com",
            "password": "pass1234",
            "fullname": "Api User",
            "national_code": "5555555555",
        }

        res = self.client.post(self.url, payload, format="json")

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["message"], "registered")
        self.assertIn("user_id", res.data)
        self.assertIsNotNone(res.data["user_id"])

    def test_register_invalid_missing_email_should_400(self):
        payload = {
            "phone": "09120000061",
            "email": "",
            "password": "pass1234",
            "fullname": "Bad Api User",
            "national_code": "6666666666",
        }
        res = self.client.post(self.url, payload, format="json")
        self.assertEqual(res.status_code, 400)

    def test_register_invalid_empty_phone_should_400(self):
        payload = {
            "phone": "",
            "email": "badphone@test.com",
            "password": "pass1234",
            "fullname": "Bad Phone User",
            "national_code": "7777777777",
        }
        res = self.client.post(self.url, payload, format="json")
        self.assertEqual(res.status_code, 400)

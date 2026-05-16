import uuid
from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.utils import timezone

from rest_framework.test import APIClient
from rest_framework import status

from apps.notifications.models import Notification, NotificationChannel, NotificationStatus
from apps.notifications.templates import NotificationTemplates
from apps.users.models import User
from apps.notifications.serializers import NotificationSerializer
from apps.notifications.services import NotificationService


class NotificationModelTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            password="testpass123",
            phone="091450000949"
            , email="teest@gmail.com"
        )

    def test_notification_model_defaults(self):
        notification = Notification.objects.create(
            user=self.user,
            title="Test Title",
            message="Test Message",
        )

        self.assertIsInstance(notification.id, uuid.UUID)
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.channel, NotificationChannel.IN_APP)
        self.assertEqual(notification.status, NotificationStatus.PENDING)
        self.assertFalse(notification.is_read)
        self.assertEqual(notification.metadata, {})
        self.assertIsNone(notification.sent_at)
        self.assertIsNone(notification.read_at)
        self.assertIsNotNone(notification.created_at)

    def test_notification_model_custom_values(self):
        now = timezone.now()

        notification = Notification.objects.create(
            user=self.user,
            title="Custom Title",
            message="Custom Message",
            channel=NotificationChannel.EMAIL,
            status=NotificationStatus.SENT,
            is_read=True,
            metadata={"key": "value"},
            sent_at=now,
            read_at=now,
        )

        self.assertEqual(notification.channel, NotificationChannel.EMAIL)
        self.assertEqual(notification.status, NotificationStatus.SENT)
        self.assertTrue(notification.is_read)
        self.assertEqual(notification.metadata, {"key": "value"})
        self.assertEqual(notification.sent_at, now)
        self.assertEqual(notification.read_at, now)

    def test_notification_ordering(self):
        n1 = Notification.objects.create(user=self.user, title="Old",
                                         message="Old msg")
        n2 = Notification.objects.create(user=self.user, title="New",
                                         message="New msg")

        # Ensure a clear time difference for ordering
        Notification.objects.filter(id=n1.id).update(
            created_at=timezone.now() - timedelta(minutes=5)
        )
        Notification.objects.filter(id=n2.id).update(
            created_at=timezone.now()
        )

        notifications = Notification.objects.filter(user=self.user)  # Ordering is applied from Meta
        self.assertEqual(notifications[0].id, n2.id)
        self.assertEqual(notifications[1].id, n1.id)


class NotificationSerializerTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            password="testpass123",
            phone="091450000949"
            , email="teest@gmail.com",
            national_code="1111111111"
        )
        self.other_user = User.objects.create_user(
            password="testpass123",
            phone="091459000949"
            , email="tee2st@gmail.com",
            national_code="2222222222"
        )

    def test_notification_serializer_data(self):
        notification = Notification.objects.create(
            user=self.user,
            title="Title",
            message="Message"
        )

        serializer = NotificationSerializer(notification)
        data = serializer.data

        self.assertEqual(data["id"], str(notification.id))
        self.assertEqual(data["user"], self.user.id)
        self.assertEqual(data["title"], "Title")
        self.assertEqual(data["message"], "Message")
        self.assertIn("created_at", data)
        self.assertIn("status", data)
        self.assertIn("channel", data)

    def test_user_is_read_only(self):
        notification = Notification.objects.create(
            user=self.user,
            title="Title",
            message="Message"
        )

        data = {
            "user": self.other_user.id,
            "title": "Updated Title",
            "message": "Updated Message",
        }

        serializer = NotificationSerializer(notification, data=data,
                                            partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        obj = serializer.save()

        self.assertEqual(obj.user, self.user)


class NotificationServiceTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            password="testpass123",
            phone="091450000949"
            , email="teest@gmail.com"
        )

    def test_create(self):
        notification = NotificationService.create(
            user=self.user,
            title="Hello",
            message="World"
        )

        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.title, "Hello")
        self.assertEqual(notification.message, "World")
        self.assertEqual(notification.status, NotificationStatus.PENDING)
        self.assertEqual(notification.metadata, {})
        self.assertIsNone(notification.sent_at)

    def test_create_with_metadata(self):
        notification = NotificationService.create(
            user=self.user,
            title="Hello",
            message="World",
            metadata={"a": 1}
        )

        self.assertEqual(notification.metadata, {"a": 1})

    @patch("apps.notifications.services.NotificationService.create")
    def test_send(self, mock_create):
        mock_notification = MagicMock()
        mock_create.return_value = mock_notification

        test_user = self.user
        test_title = "Title"
        test_message = "Message"

        result = NotificationService.send(
            user=test_user,
            title=test_title,
            message=test_message,
        )

        self.assertEqual(result, mock_notification)

        mock_create.assert_called_once_with(
            user=test_user,
            title=test_title,
            message=test_message,
            channel='IN_APP',
            metadata=None
        )

    def test_send_template(self):
        notification = NotificationService.send_template(
            user=self.user,
            template=NotificationTemplates.OTP_SENT,
            code="123456"
        )

        self.assertEqual(notification.title, "OTP Code")
        self.assertEqual(notification.message,
                         "Your verification code is 123456")
        self.assertEqual(notification.status, NotificationStatus.SENT)

    def test_mark_read(self):
        notification = Notification.objects.create(
            user=self.user,
            title="Title",
            message="Message",
            status=NotificationStatus.SENT,
            is_read=False,
        )

        NotificationService.mark_read(notification)
        notification.refresh_from_db()

        self.assertTrue(notification.is_read)
        self.assertEqual(notification.status, NotificationStatus.READ)
        self.assertIsNotNone(notification.read_at)

    def test_broadcast(self):
        user2 = User.objects.create_user(
            password="tetpass123",
            phone="091650000949"
            , email="tee3st@gmail.com",
            national_code="3222222222"

        )
        user3 = User.objects.create_user(
            password="tstpass123",
            phone="091490000949"
            , email="tee7st@gmail.com",
            national_code="4222222222"

        )

        NotificationService.broadcast(
            users=[self.user, user2, user3],
            title="Broadcast Title",
            message="Broadcast Message"
        )

        self.assertEqual(self.user.notifications.count(), 1)
        self.assertEqual(user2.notifications.count(), 1)
        self.assertEqual(user3.notifications.count(), 1)


class NotificationTemplatesTestCase(TestCase):

    def test_login_success_template(self):
        self.assertEqual(NotificationTemplates.LOGIN_SUCCESS["title"],
                         "Login Successful")
        self.assertEqual(NotificationTemplates.LOGIN_SUCCESS["message"],
                         "You logged in successfully.")

    def test_otp_sent_template(self):
        self.assertEqual(NotificationTemplates.OTP_SENT["title"],
                         "OTP Code")
        self.assertIn("{code}",
                      NotificationTemplates.OTP_SENT["message"])

    def test_all_templates_have_title_and_message(self):
        templates = [
            NotificationTemplates.LOGIN_SUCCESS,
            NotificationTemplates.OTP_SENT,
            NotificationTemplates.TRANSFER_SUCCESS,
            NotificationTemplates.LOAN_APPROVED,
            NotificationTemplates.INSTALLMENT_DUE,
            NotificationTemplates.FRAUD_ALERT,
        ]

        for template in templates:
            self.assertIn("title", template)
            self.assertIn("message", template)
            self.assertIsInstance(template["title"], str)
            self.assertIsInstance(template["message"], str)


class NotificationAPITestCase(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            password="tstpass123",
            phone="091490000949"
            , email="tee7st@gmail.com",
            national_code="4222222222"
        )
        self.other_user = User.objects.create_user(
            password="tsmtpass123",
            phone="091480000949"
            , email="tee9st@gmail.com",
            national_code="8222222222"
        )

    def test_my_notifications_requires_auth(self):
        response = self.client.get("/notifications/my/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_my_notifications_view(self):
        n1 = Notification.objects.create(
            user=self.user,
            title="Notification 1",
            message="Message 1"
        )
        Notification.objects.create(
            user=self.other_user,
            title="Notification 2",
            message="Message 2"
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get("/notifications/my/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], str(n1.id))

    def test_mark_as_read_view(self):
        notification = Notification.objects.create(
            user=self.user,
            title="Title",
            message="Message"
        )

        self.client.force_authenticate(user=self.user)
        response = (
            self.client.post(f"/notifications/{notification.id}/read/"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"detail": "read"})

        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertEqual(notification.status, "READ")
        self.assertIsNotNone(notification.read_at)

    def test_mark_as_read_view_other_user_notification(self):
        notification = Notification.objects.create(
            user=self.user,
            title="Title",
            message="Message"
        )

        self.client.force_authenticate(user=self.other_user)
        response = self.client.post(f"/notifications/{notification.id}/read/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unread_count_view(self):
        Notification.objects.create(
            user=self.user,
            title="Unread 1",
            message="Msg 1",
            is_read=False
        )
        Notification.objects.create(
            user=self.user,
            title="Unread 2",
            message="Msg 2",
            is_read=False
        )
        Notification.objects.create(
            user=self.user,
            title="Read",
            message="Msg 3",
            is_read=True
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get("/notifications/unread-count/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"unread": 2})

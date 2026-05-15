from django.utils import timezone
from .models import Notification, NotificationStatus
from .templates import NotificationTemplates


class NotificationService:

    @staticmethod
    def create(user, title, message, channel="IN_APP", metadata=None):
        return Notification.objects.create(
            user=user,
            title=title,
            message=message,
            channel=channel,
            metadata=metadata or {}
        )

    @staticmethod
    def send(user, title, message, channel="IN_APP", metadata=None):

        obj = NotificationService.create(
            user=user,
            title=title,
            message=message,
            channel=channel,
            metadata=metadata
        )

        # Future Celery Task
        obj.status = NotificationStatus.SENT
        obj.sent_at = timezone.now()
        obj.save(update_fields=["status", "sent_at"])

        return obj

    @staticmethod
    def send_template(user, template, **kwargs):

        title = template["title"]
        message = template["message"].format(**kwargs)

        return NotificationService.send(
            user=user,
            title=title,
            message=message
        )

    @staticmethod
    def mark_read(notification):

        notification.is_read = True
        notification.status = NotificationStatus.READ
        notification.read_at = timezone.now()
        notification.save(
            update_fields=["is_read", "status", "read_at"]
        )

    @staticmethod
    def broadcast(users, title, message):

        for user in users:
            NotificationService.send(user, title, message)
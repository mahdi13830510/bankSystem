from django.utils import timezone
from .models import Installment
from .services import InstallmentService
from apps.notifications.services import NotificationService
from ..notifications.templates import NotificationTemplates


def check_overdue_installments():

    today = timezone.now().date()

    items = Installment.objects.filter(
        due_date__lt=today,
        status="PENDING"
    )

    for ins in items:
        InstallmentService.apply_penalty(ins)


def send_due_reminders():

    tomorrow = timezone.now().date() + timezone.timedelta(days=1)

    items = Installment.objects.filter(
        due_date=tomorrow,
        status="PENDING"
    )

    for ins in items:
        NotificationService.send_template(
            ins.loan.customer,
            NotificationTemplates.INSTALLMENT_DUE
        )
import uuid
from django.db import models


class FraudDecision(models.TextChoices):
    SAFE = "SAFE"
    SUSPICIOUS = "SUSPICIOUS"
    BLOCKED = "BLOCKED"


class FraudReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    transaction_id = models.UUIDField()

    user_id = models.UUIDField()

    score = models.IntegerField()  # 0-100

    decision = models.CharField(
        max_length=20,
        choices=FraudDecision.choices
    )

    reason = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "fraud_reports"

from apps.auditlogs.services import AuditLogService
from apps.fraud.models import FraudReport
from apps.fraud.services.risk_engine import RiskEngine
from apps.fraud.services.rules import FraudRules
from apps.notifications.services import NotificationService
from apps.notifications.templates import NotificationTemplates


class FraudService:

    @staticmethod
    def check_transaction(*, user, transaction, ip):

        history_count = transaction.account.transactions.count()

        score = RiskEngine.calculate_score(
            transaction=transaction,
            ip=ip,
            history_count=history_count
        )

        decision = FraudRules.decide(score)

        report = FraudReport.objects.create(
            transaction_id=transaction.id,
            user_id=user.id,
            score=score,
            decision=decision,
            reason={
                "amount": str(transaction.amount),
                "ip": ip,
                "history": history_count,
                "model": "isolation_forest_v1",
            }
        )

        if decision == "BLOCKED":
            raise Exception("Transaction blocked by fraud system")

        if decision in ("BLOCKED", "SUSPICIOUS"):
            AuditLogService.critical(
                actor=user,
                action="FRAUD_DECISION",
                metadata={"risk_score": score, "decision": decision}
            )
            NotificationService.send_template(
                user,
                NotificationTemplates.FRAUD_ALERT
            )
        return report
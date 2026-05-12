from apps.fraud.models import FraudReport
from apps.fraud.services.risk_engine import RiskEngine
from apps.fraud.services.rules import FraudRules


class FraudService:

    @staticmethod
    def check_transaction(*, user, transaction, ip):

        history_count = transaction.account.transactions.count()

        score = RiskEngine.calculate_score(
            user=user,
            amount=transaction.amount,
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
                "history": history_count
            }
        )

        if decision == "BLOCKED":
            raise Exception("Transaction blocked by fraud system")

        return report
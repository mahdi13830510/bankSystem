from apps.banks.models import BankStatus


class RiskEngine:

    @staticmethod
    def calculate_score(
            *,
            transaction,
            ip,
            history_count
    ):

        score = 0

        amount = transaction.amount
        source_bank = transaction.account.bank
        destination_bank = transaction.destination_account.bank

        # amount risk
        if amount > 5000:
            score += 30

        if amount > 10000:
            score += 20

        # velocity
        if history_count > 5:
            score += 20

        # destination bank risk
        if destination_bank.status == BankStatus.SUSPENDED:
            score += 50

        elif destination_bank.status == BankStatus.MAINTENANCE:
            score += 25

        # interbank risk
        if source_bank.id != destination_bank.id:
            score += 10

        return min(score, 100)

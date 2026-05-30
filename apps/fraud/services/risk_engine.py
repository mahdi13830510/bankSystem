from apps.fraud.services.ml_scoring import MLScoringService

TXN_TYPE_MAP = {
    "CARD_TO_CARD": 0,
    "INTERNAL_TRANSFER": 1,
    "IBAN_TRANSFER": 2,
    "CASH_DEPOSIT": 3,
    "CASH_WITHDRAW": 4,
    "LOAN_DISBURSEMENT": 5,
    "INSTALLMENT_PAYMENT": 6,
    "LATE_FEE": 7,
    "LOAN_SETTLEMENT": 8,
    "REFUND": 9,
}


class RiskEngine:

    @staticmethod
    def calculate_score(*, transaction, ip, history_count) -> int:

        amount = float(transaction.amount)
        fee = float(transaction.fee) if transaction.fee else 0
        created_at = transaction.created_at
        hour = created_at.hour if created_at else 12
        is_weekend = int(created_at.weekday() >= 5) if created_at else 0
        fee_ratio = (fee / amount) if amount > 0 else 0
        txn_type_enc = TXN_TYPE_MAP.get(transaction.type, 0)

        # try to detect interbank from destination if available
        is_interbank = 0
        try:
            src_bank = transaction.account.bank_id
            dst_bank = transaction.destination_account.bank_id
            is_interbank = int(src_bank != dst_bank)
        except AttributeError:
            is_interbank = 0

        features = {
            "amount": amount,
            "hour_of_day": hour,
            "is_weekend": is_weekend,
            "is_interbank": is_interbank,
            "history_count": history_count,
            "fee_ratio": fee_ratio,
            "txn_type_encoded": txn_type_enc,
        }

        ml_score = MLScoringService.predict(features)

        # rule-based boosts (deterministic, always applied)
        rule_boost = 0
        if amount > 10000:
            rule_boost += 20
        elif amount > 5000:
            rule_boost += 10
        if history_count < 3:
            rule_boost += 15
        if hour < 5 or hour >= 23:
            rule_boost += 15
        if is_interbank:
            rule_boost += 5

        # 70 % ML weight, 30 % rule boosts
        combined = int(ml_score * 0.7 + rule_boost * 0.3)
        return min(combined, 100)

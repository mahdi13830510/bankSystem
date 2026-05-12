class RiskEngine:

    @staticmethod
    def calculate_score(*, user, amount, ip, history_count):

        score = 0

        # amount anomaly
        if amount > 5000:
            score += 30
        if amount > 10000:
            score += 50

        # velocity check
        if history_count > 5:
            score += 25

        # new device / ip risk
        if ip.startswith("10."):
            score += 10

        return min(score, 100)
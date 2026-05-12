class FraudRules:

    @staticmethod
    def decide(score):

        if score >= 80:
            return "BLOCKED"

        if score >= 50:
            return "SUSPICIOUS"

        return "SAFE"
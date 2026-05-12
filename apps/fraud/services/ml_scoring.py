class MLScoringService:

    @staticmethod
    def predict(features: dict):

        # placeholder model
        # در real system: sklearn / tensorflow

        if features["amount"] > 8000:
            return 70

        return 20
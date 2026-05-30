import numpy as np
from django.core.management.base import BaseCommand
from apps.fraud.services.ml_scoring import MLScoringService


def _gen_normal(n, rng):
    return np.column_stack([
        rng.lognormal(6.5, 1.2, n).clip(10, 9000),
        rng.choice(np.arange(8, 22), n).astype(float),
        rng.binomial(1, 0.28, n).astype(float),
        rng.binomial(1, 0.35, n).astype(float),
        rng.poisson(12, n).clip(0, 100).astype(float),
        rng.uniform(0.001, 0.03, n),
        rng.integers(0, 10, n).astype(float),
    ])


def _gen_fraud(n, rng):
    return np.column_stack([
        rng.lognormal(9.5, 0.8, n).clip(5000, 200000),
        rng.choice([0, 1, 2, 3, 4, 23], n).astype(float),
        np.ones(n), np.ones(n),
        rng.poisson(1, n).clip(0, 5).astype(float),
        rng.uniform(0.0001, 0.005, n),
        rng.integers(0, 10, n).astype(float),
    ])


class Command(BaseCommand):
    help = "Generate synthetic data and train the IsolationForest fraud model"

    def add_arguments(self, parser):
        parser.add_argument("--samples", type=int, default=50000)

    def handle(self, *args, **options):
        n = options["samples"]
        rng = np.random.default_rng(42)

        self.stdout.write(f"Generating {n} normal + {n // 20} fraud samples...")
        X_normal = _gen_normal(n, rng)
        X_fraud  = _gen_fraud(n // 20, rng)

        MLScoringService.train_and_save(X_normal, X_fraud)
        self.stdout.write(self.style.SUCCESS("Model trained and saved."))

        normal_score = MLScoringService.predict({
            "amount": 500, "hour_of_day": 14, "is_weekend": 0,
            "is_interbank": 0, "history_count": 15, "fee_ratio": 0.01,
            "txn_type_encoded": 1,
        })
        fraud_score = MLScoringService.predict({
            "amount": 95000, "hour_of_day": 2, "is_weekend": 1,
            "is_interbank": 1, "history_count": 0, "fee_ratio": 0.001,
            "txn_type_encoded": 1,
        })
        self.stdout.write(f"Sanity — normal: {normal_score}, fraud: {fraud_score}")

"""Standalone training script — no Django required."""
import os
import numpy as np
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

HERE = os.path.dirname(os.path.abspath(__file__))

def gen_normal(n, rng):
    amount       = rng.lognormal(mean=6.5, sigma=1.2, size=n).clip(10, 9000)
    hour         = rng.choice(np.arange(8, 22), size=n).astype(float)
    is_weekend   = rng.binomial(1, 0.28, size=n).astype(float)
    is_interbank = rng.binomial(1, 0.35, size=n).astype(float)
    history      = rng.poisson(lam=12, size=n).clip(0, 100).astype(float)
    fee_ratio    = rng.uniform(0.001, 0.03, size=n)
    txn_type     = rng.integers(0, 10, size=n).astype(float)
    return np.column_stack([amount, hour, is_weekend, is_interbank,
                            history, fee_ratio, txn_type])

def gen_fraud(n, rng):
    amount       = rng.lognormal(mean=9.5, sigma=0.8, size=n).clip(5000, 200000)
    hour         = rng.choice([0, 1, 2, 3, 4, 23], size=n).astype(float)
    is_weekend   = np.ones(n)
    is_interbank = np.ones(n)
    history      = rng.poisson(lam=1, size=n).clip(0, 5).astype(float)
    fee_ratio    = rng.uniform(0.0001, 0.005, size=n)
    txn_type     = rng.integers(0, 10, size=n).astype(float)
    return np.column_stack([amount, hour, is_weekend, is_interbank,
                            history, fee_ratio, txn_type])

if __name__ == "__main__":
    rng = np.random.default_rng(42)
    n_normal = 50000
    n_fraud  = 2500

    print(f"Generating {n_normal} normal + {n_fraud} fraud samples...")
    X_normal = gen_normal(n_normal, rng)
    X_fraud  = gen_fraud(n_fraud, rng)
    X_all    = np.vstack([X_normal, X_fraud])

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_all)

    print("Training IsolationForest (n_estimators=200)...")
    model = IsolationForest(n_estimators=200, contamination=0.05,
                            random_state=42, n_jobs=-1)
    model.fit(X_scaled)

    # calibrate: use p2 of normal as "safe ceiling" and p98 of fraud as "danger floor"
    raw_normal = model.score_samples(scaler.transform(X_normal))
    raw_fraud  = model.score_samples(scaler.transform(X_fraud))
    score_low  = float(np.percentile(raw_normal, 95))   # most-normal threshold
    score_high = float(np.percentile(raw_fraud,   5))   # most-fraudulent threshold
    print(f"Calibration: safe_ceiling={score_low:.4f}  danger_floor={score_high:.4f}")

    artifact = {"model": model, "scaler": scaler,
                "score_low": score_low, "score_high": score_high}
    joblib.dump(artifact, os.path.join(HERE, "fraud_artifact.pkl"))
    print("Saved fraud_artifact.pkl")

    # sanity check
    for label, vec in [("Normal", [500, 14, 0, 0, 15, 0.01, 1]),
                       ("Fraud",  [95000, 2, 1, 1, 0, 0.001, 1])]:
        raw = model.score_samples(scaler.transform([vec]))[0]
        score = int(np.clip((raw - score_low) / (score_high - score_low) * 100, 0, 100))
        print(f"{label} txn → raw={raw:.4f}  score={score}")

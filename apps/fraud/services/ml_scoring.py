import os
import numpy as np
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

ARTIFACT_PATH = os.path.join(os.path.dirname(__file__), "..", "ml", "fraud_artifact.pkl")

_artifact = None


def _load():
    global _artifact
    if _artifact is None and os.path.exists(ARTIFACT_PATH):
        _artifact = joblib.load(ARTIFACT_PATH)


def _features_to_vector(features: dict) -> list:
    return [[
        float(features.get("amount", 0)),
        float(features.get("hour_of_day", 12)),
        float(features.get("is_weekend", 0)),
        float(features.get("is_interbank", 0)),
        float(features.get("history_count", 0)),
        float(features.get("fee_ratio", 0)),
        float(features.get("txn_type_encoded", 0)),
    ]]


class MLScoringService:

    @staticmethod
    def predict(features: dict) -> int:
        """Return fraud score 0-100. Higher = more suspicious."""
        _load()

        if _artifact is None:
            return 60 if features.get("amount", 0) > 8000 else 20

        model: IsolationForest = _artifact["model"]
        scaler: StandardScaler = _artifact["scaler"]
        score_low: float       = _artifact["score_low"]
        score_high: float      = _artifact["score_high"]

        vec = _features_to_vector(features)
        scaled = scaler.transform(vec)
        raw = model.score_samples(scaled)[0]

        # raw: more negative = more anomalous
        # score_low (p95 of normal) → 0,  score_high (p5 of fraud) → 100
        score = int(np.clip(
            (raw - score_low) / (score_high - score_low) * 100,
            0, 100
        ))
        return score

    @staticmethod
    def train_and_save(X_normal: np.ndarray, X_fraud: np.ndarray):
        from sklearn.ensemble import IsolationForest
        X_all = np.vstack([X_normal, X_fraud])
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_all)

        model = IsolationForest(n_estimators=200, contamination=0.05,
                                random_state=42, n_jobs=-1)
        model.fit(X_scaled)

        raw_normal = model.score_samples(scaler.transform(X_normal))
        raw_fraud  = model.score_samples(scaler.transform(X_fraud))
        score_low  = float(np.percentile(raw_normal, 95))
        score_high = float(np.percentile(raw_fraud,   5))

        artifact = {"model": model, "scaler": scaler,
                    "score_low": score_low, "score_high": score_high}
        os.makedirs(os.path.dirname(ARTIFACT_PATH), exist_ok=True)
        joblib.dump(artifact, ARTIFACT_PATH)

        global _artifact
        _artifact = artifact

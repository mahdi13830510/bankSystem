# BankSystem

A Django REST banking backend with ML-powered fraud detection.

## Apps

| App | Purpose |
|---|---|
| `users` | User accounts and profiles |
| `authentication` | JWT sessions |
| `banks` | Bank and branch registry |
| `accounts` | Customer bank accounts |
| `transactions` | Transfers, deposits, withdrawals |
| `loans` | Loan origination and management |
| `installments` | Installment schedules and payments |
| `fraud` | ML fraud detection (IsolationForest) |
| `notifications` | In-app notifications |
| `auditlogs` | Immutable audit trail |
| `support_ai` | LLM-powered customer support |
| `dashboard` | KPI and analytics aggregation |

## Setup

```bash
cp .env.example .env          # set DEBUG=True for local dev
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py train_fraud_model   # train the ML fraud model
python manage.py runserver
```

## Fraud Detection

### How it works

Every transfer triggers a fraud check before balances are modified.

1. **ML scoring** - `IsolationForest` trained on 50,000 synthetic normal transactions detects anomalies.
2. **Rule boosts** - deterministic penalties for high amounts, odd hours, low account history, interbank transfers.
3. **Combined score** - `score = ml_score * 0.7 + rule_boosts * 0.3` (0-100).
4. **Decision**
   - `score < 50` -> SAFE
   - `50 <= score < 80` -> SUSPICIOUS (logged + user notified)
   - `score >= 80` -> BLOCKED (transaction aborted)

### Features fed to the model

| Feature | Description |
|---|---|
| `amount` | Transaction amount |
| `hour_of_day` | Hour the transaction was initiated (0-23) |
| `is_weekend` | 1 if Saturday or Sunday |
| `is_interbank` | 1 if source and destination banks differ |
| `history_count` | Total prior transactions on the source account |
| `fee_ratio` | fee / amount |
| `txn_type_encoded` | Integer encoding of transaction type |

### Training commands

```bash
# Train with default 50,000 samples (fast, ~10s)
python manage.py train_fraud_model

# Train with more samples for a sharper decision boundary
python manage.py train_fraud_model --samples 200000

# Standalone script (no Django environment needed)
python apps/fraud/ml/train.py
```

The trained artifact is saved to `apps/fraud/ml/fraud_artifact.pkl` and loaded lazily on first prediction.

### Retraining with real data

When real labeled transactions become available, replace the synthetic data generators in `train.py` with a DB query:

```python
# Example: load from Django ORM
from apps.transactions.models import Transaction
from apps.fraud.models import FraudReport

# build feature matrix from real records, pass to MLScoringService.train_and_save()
```

### Admin panel

Navigate to `/admin/` after creating a superuser.

The **Fraud Reports** section provides:

- List view with color-coded score bars and decision badges
- Summary cards (total / blocked / suspicious / average score) at the top of the list
- Per-report detail with formatted JSON reason and visual score bar
- Bulk actions:
  - **Override to SAFE** - manually clear false positives
  - **Override to BLOCKED** - escalate suspicious reports
  - **Re-score** - re-run the current model against stored feature data
- **ML Model Dashboard** button (top-right of list) - separate page showing:
  - Model parameters (algorithm, n_estimators, contamination, calibration bounds)
  - Scaler statistics (mean and std for each feature)
  - Score distribution histogram of recent reports
  - Live score tester - enter feature values and see the ML score, combined score, and decision instantly
  - Management command reference

## API

Base path: `/api/v1/`

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/auth/login/` | Obtain JWT token |
| POST | `/api/v1/auth/logout/` | Invalidate session |
| GET | `/api/v1/users/me/` | Current user profile |
| GET/POST | `/accounts/` | Account list / create |
| POST | `/api/transactions/transfer/` | Card-to-card transfer |
| POST | `/api/transactions/iban/` | IBAN transfer |
| GET | `/fraud/reports/` | Fraud report list |

Full interactive docs available at `/swagger/` (drf-yasg).

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `DEBUG` | `False` | Enable debug mode |
| `SECRET_KEY` | (set in settings) | Django secret key - change in production |

## Running tests

```bash
python manage.py test apps.fraud
python manage.py test              # all apps
```

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

#Notifications app APIs

| Method | Path | Permission |
|---|---|---|
| Get | `/notifications/my/` | Customer | 
| Get | `/notifications/unread-count/` | Customer | 
| POST | `/notifications/mark-all-read/` | Customer | 
| POST | `/notifications/<pk>/read/` | Customer | 
| GET | `/notifications/admin/` | Admin | 
| POST | `/notifications/admin/send` | Admin | 
| POST | `/notifications/admin/broadcast/` | Admin | 
| GET | `/notifications/admin/users/<user_id>/` | Admin | 
| DELETE | `/notifications/admin/<pk>/delete/` | Admin | 

#Transactions App APIs

| Method | Path | Permission |
|---|---|---|
| POST | `/api/transactions/card-transfer/` | Customer | 
| POST | `/api/transactions/iban-transfer/` | Customer | 
| GET | `/api/transactions/statement/<account_id>/` | Customer | 
| GET | `/api/transactions/limits/<account_id>/usage/` | Customer | 
| GET | `/api/transactions/admin/` | Admin | 
| GET | `/api/transactions/admin/<pk>/` | Admin | 
| GET | `/api/transactions/admin/ref/<reference>/` | Admin | 
| GET | `/api/transactions/admin/account/<id>/statement/` | Admin | 
| POST | `/api/transactions/admin/<pk>/reverse/` | Admin | 
| POST | `/api/transactions/admin/account/<id>/limits/reset/` | Admin | 
| GET | `/api/transactions/admin/account/<id>/limits/usage/` | Admin | 


#Loans App APIs 

| Method | Path | Permission |  
|---|---|---|
| GET | `/loans/my-requests/<pk>/` | Customer | 
| GET | `/loans/my-loans/<pk>/` | Customer | 
| GET | `/loans/admin/requests/` | Admin | 
| GET | `/loans/admin/requests/pending/` | Admin | 
| GET | `/loans/admin/requests/pending/` | Admin | 
| GET | `/loans/admin/requests/<pk>/` | Admin | 
| POST | `/loans/admin/requests/<pk>/evaluate/` | Admin | 
| POST | `/loans/admin/requests/<pk>/approve/` | Admin | 
| POST | `/loans/admin/requests/<pk>/reject/` | Admin | 
| GET | `/loans/admin/loans/` | Admin | 
| GET | `/loans/admin/loans/<pk>/` | Admin | 
| POST | `/loans/admin/loans/<pk>/status/` | Admin | 
| GET | `/loans/admin/customer/<id>/loans/` | Admin | 
| POST | `/loans/admin/customer/<id>/requests/` | Admin | 

#Installments App APIs 

| Method | Path | Permission | 
|---|---|---|
| GET | `/installments/my/<pk>/` | Customer | 
| GET | `/installments/my/loan/<loan_id>/` | Customer | 
| POST | `/installments/<pk>/pay/` | Customer | 
| GET | `/installments/admin/` | Admin | 
| GET | `/installments/admin/overdue/` | Admin | 
| GET | `/installments/admin/<pk>/` | Admin | 
| POST | `/installments/admin/<pk>/penalty/` | Admin | 
| GET | `/installments/admin/loan/<loan_id>/` | Admin | 
| GET | `/installments/admin/loan/<loan_id>/remaining/` | Admin | 

#Users App APIs 

| Method | Path | Permission | 
|---|---|---|
| POST | `/api/v1/users/register` | Public | 
| GET | `/api/v1/users/me/` | Customer | 
| POST | `/api/v1/users/me/change-password/` | Customer | 
| GET/PATCH | `/api/v1/users/me/profile/` | Customer | 
| GET | `/api/v1/users/me/devices/` | Customer | 
| DELETE | `/api/v1/users/me/devices/<pk>/` | Customer | 
| GET | `/api/v1/users/admin/` | Admin | 
| GET/PATCH | `/api/v1/users/admin/<pk>/` | Admin | 
| POST | `/api/v1/users/admin/<pk>/verify/` | Admin | 
| POST | `/api/v1/users/admin/<pk>/block/` | Admin | 
| POST | `/api/v1/users/admin/<pk>/unblock/` | Admin | 
| POST | `/api/v1/users/admin/<pk>/suspend/` | Admin | 
| POST | `/api/v1/users/admin/<pk>/activate/` | Admin | 
| POST | `/api/v1/users/admin/<pk>/change-role/` | Admin | 
| POST | `/api/v1/users/admin/<pk>/reset-attempts/` | Admin | 
| POST | `/api/v1/users/admin/<pk>/reset-password/` | Admin | 
| GET/PATCH | `/api/v1/users/admin/<pk>/profile/` | Admin | 
| GET | `/api/v1/users/admin/<pk>/devices/` | Admin | 
| DELETE | `/api/v1/users/admin/<pk>/devices/<device_pk>/` | Admin | 

#Authentication app APIs 

| Method | Path | Permission |
|---|---|---|
| POST | `/api/v1/auth/refresh/` | Public | 
| GET | `/api/v1/auth/sessions/my/` | Customer | 
| POST | `/api/v1/auth/sessions/my/<pk>/revoke/` | Customer | 
| POST | `/api/v1/auth/sessions/revoke-others/` | Customer | 
| GET | `/api/v1/auth/admin/sessions/` | Admin | 
| GET | `/api/v1/auth/admin/sessions/<pk>/` | Admin | 
| POST | `/api/v1/auth/admin/sessions/<pk>/revoke/` | Admin | 
| GET | `/api/v1/auth/admin/users/<id>/sessions/` | Admin | 
| POST | `/api/v1/auth/admin/users/<id>/sessions/revoke-all/` | Admin | 
| GET | `/api/v1/auth/admin/users/<id>/otps/` | Admin | 
| POST | `/api/v1/auth/admin/users/<id>/otps/invalidate/` | Admin | 

#Accounts App APIs 

| Method | Path | Permission | 
|---|---|---|
| POST | `/accounts/<pk>/set-primary/` | Customer | 
| POST | `/accounts/<pk>/withdraw/` | Staff | 
| GET | `/accounts/admin/` | Staff | 
| GET | `/accounts/admin/stats/` | Admin | 
| POST | `/accounts/admin/open/` | Admin | 
| GET | `/accounts/admin/<pk>/` | Staff | 
| POST | `/accounts/admin/<pk>/set-primary/` | Admin | 
| GET | `/accounts/admin/number/<account_number>/` | Staff | 
| GET | `/accounts/admin/iban/<iban>/` | Staff | 
| GET | `/accounts/admin/customer/<id>/` | Staff | 
| POST | `/accounts/admin/<pk>/block-balance/` | Admin | 
| POST | `/accounts/admin/<pk>/unblock-balance/` | Admin | 


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

from django.utils import timezone

from apps.accounts.services import AccountService
from apps.transactions.services import TransactionService
from apps.loans.services import LoanService
from apps.installments.services import InstallmentService
from apps.notifications.services import NotificationService

from apps.loans.models import Loan
from apps.installments.models import Installment
from apps.accounts.models import Account

from apps.ai_agent.models import PendingAction
from apps.auditlogs.services import AuditLogService


class ActionExecutor:

    @staticmethod
    def balance(user):
        account = AccountService.get_primary_account(user)

        return {
            "type": "balance",
            "account_number": account.account_number,
            "iban": account.iban,
            "balance": str(account.balance),
            "currency": account.currency,
            "status": account.status,
        }

    @staticmethod
    def my_accounts(user):
        accounts = AccountService.my_accounts(user)

        return {
            "type": "accounts",
            "items": [
                {
                    "id": acc.id,
                    "account_number": acc.account_number,
                    "iban": acc.iban,
                    "balance": str(acc.balance),
                    "currency": acc.currency,
                    "status": acc.status,
                    "is_primary": acc.is_primary,
                }
                for acc in accounts
            ],
        }

    @staticmethod
    def statement(user):
        account = AccountService.get_primary_account(user)
        txns = TransactionService.get_statement(account)[:20]

        return {
            "type": "statement",
            "transactions": [
                {
                    "id": str(tx.id),
                    "amount": str(tx.amount),
                    "fee": str(tx.fee),
                    "transaction_type": tx.type,
                    "status": tx.status,
                    "reference_number": tx.reference_number,
                    "created_at": tx.created_at,
                }
                for tx in txns
            ],
        }

    @staticmethod
    def my_loans(user):
        loans = Loan.objects.filter(customer=user)

        return {
            "type": "loans",
            "items": [
                {
                    "id": str(loan.id),
                    "principal_amount": str(loan.principal_amount),
                    "total_payable": str(loan.total_payable),
                    "paid_amount": str(loan.paid_amount),
                    "status": loan.status,
                }
                for loan in loans
            ],
        }

    @staticmethod
    def my_installments(user):
        installments = Installment.objects.filter(
            loan__customer=user
        )

        return {
            "type": "installments",
            "items": [
                {
                    "id": str(inst.id),
                    "number": inst.number,
                    "amount": str(inst.amount),
                    "status": inst.status,
                    "due_date": inst.due_date,
                }
                for inst in installments
            ],
        }

    @staticmethod
    def remaining_debt(user, loan_id):
        loan = Loan.objects.get(id=loan_id, customer=user)
        debt = InstallmentService.remaining_debt(loan)

        return {
            "type": "remaining_debt",
            "loan_id": str(loan.id),
            "remaining_debt": str(debt),
        }

    @staticmethod
    def notifications(user):
        items = NotificationService.get_unread(user)

        return {
            "type": "notifications",
            "items": [
                {
                    "id": str(n.id),
                    "title": n.title,
                    "message": n.body,
                    "created_at": n.created_at,
                }
                for n in items
            ],
        }

    # ------------------------------------------------------------------ #
    #  Pending-action creators                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def create_iban_transfer(*, user, amount, iban):
        action = PendingAction.objects.create(
            user=user,
            intent="iban_transfer",
            payload={"amount": amount, "iban": iban},
            confirmation_text=f"Transfer {amount} TRY to {iban}",
            expires_at=timezone.now() + timezone.timedelta(minutes=5),
        )

        return {
            "needs_confirmation": True,
            "action_id": action.id,
            "message": (
                f"آیا انتقال {amount} TRY "
                f"به حساب {iban} انجام شود؟"
            ),
        }

    @staticmethod
    def create_loan_request(*, user, payload):
        action = PendingAction.objects.create(
            user=user,
            intent="loan_request",
            payload=payload,
            confirmation_text=f"Loan request {payload.get('amount')}",
            expires_at=timezone.now() + timezone.timedelta(minutes=5),
        )

        return {
            "needs_confirmation": True,
            "action_id": action.id,
            "message": "آیا درخواست وام ثبت شود؟",
        }

    @staticmethod
    def create_installment_payment(*, user, installment_id):
        action = PendingAction.objects.create(
            user=user,
            intent="pay_installment",
            payload={"installment_id": installment_id},
            confirmation_text=f"Installment {installment_id}",
            expires_at=timezone.now() + timezone.timedelta(minutes=5),
        )

        return {
            "needs_confirmation": True,
            "action_id": action.id,
            "message": "آیا قسط پرداخت شود؟",
        }

    # ------------------------------------------------------------------ #
    #  Action executor                                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def execute_action(action, ip_address):
        if action.is_expired():
            action.status = PendingAction.Status.EXPIRED
            action.save(update_fields=["status"])
            raise ValueError("Action has expired")

        if action.intent == "iban_transfer":
            return ActionExecutor._execute_iban_transfer(
                action, ip_address
            )

        if action.intent == "loan_request":
            return ActionExecutor._execute_loan_request(action)

        if action.intent == "pay_installment":
            return ActionExecutor._execute_pay_installment(action)

        raise ValueError(f"Unsupported action: {action.intent}")

    # ------------------------------------------------------------------ #
    #  Private helpers                                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _mark_executed(action):
        action.status = PendingAction.Status.EXECUTED
        action.executed_at = timezone.now()
        action.save(update_fields=["status", "executed_at"])

    @staticmethod
    def _execute_iban_transfer(action, ip_address):
        source = AccountService.get_primary_account(action.user)
        destination = Account.objects.get(
            iban=action.payload["iban"]
        )

        txn = TransactionService.iban_transfer(
            actor=action.user,
            source=source,
            destination=destination,
            amount=action.payload["amount"],
            ip=ip_address,
        )

        ActionExecutor._mark_executed(action)

        AuditLogService.info(
            actor=action.user,
            action="AI_IBAN_TRANSFER",
            description=f"txn={txn.id} iban={action.payload['iban']}"
        )

        return {"success": True, "transaction_id": str(txn.id)}

    @staticmethod
    def _execute_loan_request(action):
        req = LoanService.create_request(
            action.user, action.payload
        )

        ActionExecutor._mark_executed(action)

        AuditLogService.info(
            actor=action.user,
            action="AI_LOAN_REQUEST",
            description=f"loan_request={req.id}"
        )

        return {"success": True, "loan_request_id": str(req.id)}

    @staticmethod
    def _execute_pay_installment(action):
        installment = Installment.objects.get(
            id=action.payload["installment_id"],
            loan__customer=action.user,
        )

        InstallmentService.pay_installment(action.user, installment)

        ActionExecutor._mark_executed(action)

        AuditLogService.info(
            actor=action.user,
            action="AI_PAY_INSTALLMENT",
            description=f"installment={installment.id}"
        )

        return {"success": True}
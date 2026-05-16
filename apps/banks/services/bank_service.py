from apps.auditlogs.services import AuditLogService
from apps.banks.models import Bank


class BankService:

    @staticmethod
    def create_bank(*, actor, **data):
        bank = Bank.objects.create(**data)

        AuditLogService.log(
            actor=actor,
            action="ADMIN",
            metadata={"event": "BANK_CREATED"}
        )

        return bank

    @staticmethod
    def change_status(*, actor, bank, status):
        bank.status = status
        bank.save(update_fields=["status"])

        AuditLogService.log(
            actor=actor,
            action="ADMIN",
            metadata={
                "event": "BANK_STATUS_CHANGED",
                "status": status
            }
        )

        return bank

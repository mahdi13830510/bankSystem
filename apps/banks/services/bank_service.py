from apps.auditlogs.services import AuditLogService
from apps.banks.models import Bank


class BankService:

    @staticmethod
    def create_bank(*, actor, **data):

        bank = Bank.objects.create(**data)

        AuditLogService.log(
            user=actor,
            action="ADMIN",
            entity_type="Bank",
            entity_id=bank.id,
            metadata={"event": "BANK_CREATED"}
        )

        return bank

    @staticmethod
    def change_status(*, actor, bank, status):

        bank.status = status
        bank.save(update_fields=["status"])

        AuditLogService.log(
            user=actor,
            action="ADMIN",
            entity_type="Bank",
            entity_id=bank.id,
            metadata={
                "event": "BANK_STATUS_CHANGED",
                "status": status
            }
        )

        return bank
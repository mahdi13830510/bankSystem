from ..models import Bank


class RoutingService:

    @staticmethod
    def get_bank_by_iban(iban):
        prefix = iban[:5]

        return Bank.objects.filter(
            iban_prefix=prefix,
            status="ACTIVE"
        ).first()

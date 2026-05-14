from decimal import Decimal


class LoanCalculator:

    @staticmethod
    def calculate_total(amount, annual_rate, months):
        monthly_rate = Decimal(annual_rate) / Decimal("12") / Decimal("100")
        total = amount * (1 + monthly_rate * months)
        return total.quantize(Decimal("0.01"))

    @staticmethod
    def monthly_installment(total, months):
        return (total / months).quantize(Decimal("0.01"))
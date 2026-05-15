from decimal import Decimal, ROUND_HALF_UP


class Money:

    @staticmethod
    def to_decimal(value):
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def add(a, b):
        return Money.to_decimal(a) + Money.to_decimal(b)

    @staticmethod
    def subtract(a, b):
        return Money.to_decimal(a) - Money.to_decimal(b)

    @staticmethod
    def is_positive(value):
        return Money.to_decimal(value) > 0
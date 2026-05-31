from decimal import Decimal
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils import timezone


class LimitService:
    """
    Enterprise Banking Limit Engine
    --------------------------------
    Handles:
    - Daily transfer limit
    - Daily withdraw limit
    - Daily transaction count
    - Velocity checks
    - Dynamic VIP limits
    """

    DEFAULT_DAILY_TRANSFER_LIMIT = Decimal("50000.00")
    DEFAULT_DAILY_WITHDRAW_LIMIT = Decimal("10000.00")
    DEFAULT_DAILY_TXN_COUNT = 20

    VIP_TRANSFER_LIMIT = Decimal("250000.00")
    VIP_WITHDRAW_LIMIT = Decimal("50000.00")

    CACHE_EXPIRE = 86400

    # ---------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------

    @staticmethod
    def _today():
        return timezone.localdate()

    @staticmethod
    def _key(account_id, suffix):
        return f"limit:{account_id}:{LimitService._today()}:{suffix}"

    @staticmethod
    def _is_vip(account):
        return getattr(account.customer, "is_vip", False)

    @staticmethod
    def _transfer_limit(account):
        return (
            LimitService.VIP_TRANSFER_LIMIT
            if LimitService._is_vip(account)
            else LimitService.DEFAULT_DAILY_TRANSFER_LIMIT
        )

    @staticmethod
    def _withdraw_limit(account):
        return (
            LimitService.VIP_WITHDRAW_LIMIT
            if LimitService._is_vip(account)
            else LimitService.DEFAULT_DAILY_WITHDRAW_LIMIT
        )

    # ---------------------------------------------------
    # Transfer Limit
    # ---------------------------------------------------

    @staticmethod
    def validate_daily_transfer_limit(account, amount):
        key = LimitService._key(account.id, "transfer_sum")

        current = cache.get(key, Decimal("0"))
        new_total = current + Decimal(amount)

        if new_total > LimitService._transfer_limit(account):
            raise ValidationError("Daily transfer limit exceeded.")

        cache.set(key, new_total, timeout=LimitService.CACHE_EXPIRE)
        return True

    # ---------------------------------------------------
    # Withdraw Limit
    # ---------------------------------------------------

    @staticmethod
    def validate_daily_withdraw_limit(account, amount):
        key = LimitService._key(account.id, "withdraw_sum")

        current = cache.get(key, Decimal("0"))
        new_total = current + Decimal(amount)

        if new_total > LimitService._withdraw_limit(account):
            raise ValidationError("Daily withdraw limit exceeded.")

        cache.set(key, new_total, timeout=LimitService.CACHE_EXPIRE)
        return True

    # ---------------------------------------------------
    # Daily Count Limit
    # ---------------------------------------------------

    @staticmethod
    def validate_daily_transaction_count(account):
        key = LimitService._key(account.id, "txn_count")

        count = cache.get(key, 0) + 1

        if count > LimitService.DEFAULT_DAILY_TXN_COUNT:
            raise ValidationError("Daily transaction count exceeded.")

        cache.set(key, count, timeout=LimitService.CACHE_EXPIRE)
        return True

    # ---------------------------------------------------
    # Combined Validator
    # ---------------------------------------------------

    @staticmethod
    def validate_transaction(account, amount, txn_type="TRANSFER"):
        LimitService.validate_daily_transaction_count(account)

        if txn_type == "WITHDRAW":
            LimitService.validate_daily_withdraw_limit(
                account,
                amount
            )
        else:
            LimitService.validate_daily_transfer_limit(
                account,
                amount
            )

        return True

    # ---------------------------------------------------
    # Admin / Reset
    # ---------------------------------------------------

    @staticmethod
    def reset_limits(account):
        cache.delete(
            LimitService._key(account.id, "transfer_sum")
        )
        cache.delete(
            LimitService._key(account.id, "withdraw_sum")
        )
        cache.delete(
            LimitService._key(account.id, "txn_count")
        )
        return True

    # ---------------------------------------------------
    # Read Stats
    # ---------------------------------------------------

    @staticmethod
    def get_usage(account):
        return {
            "transfer_used": cache.get(
                LimitService._key(account.id, "transfer_sum"),
                Decimal("0")
            ),
            "withdraw_used": cache.get(
                LimitService._key(account.id, "withdraw_sum"),
                Decimal("0")
            ),
            "txn_count": cache.get(
                LimitService._key(account.id, "txn_count"),
                0
            ),
            "transfer_limit": LimitService._transfer_limit(account),
            "withdraw_limit": LimitService._withdraw_limit(account),
        }
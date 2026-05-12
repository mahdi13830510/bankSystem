class AccountError(Exception):
    pass


class InsufficientBalanceError(AccountError):
    pass


class InvalidAmountError(AccountError):
    pass

class CoreException(Exception):
    pass


class ValidationException(CoreException):
    pass


class InsufficientBalance(CoreException):
    pass


class UnauthorizedAction(CoreException):
    pass


class NotFoundException(CoreException):
    pass


class FraudDetectedException(CoreException):
    pass
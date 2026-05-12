from rest_framework.permissions import BasePermission


class IsAuthenticatedBankUser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and (
                    request.user.is_superuser
                    or request.user.is_staff
                    or getattr(request.user, "role", None) == "admin"
            )
        )


class IsBankStaff(BasePermission):
    def has_permission(self, request, view):
        return bool(getattr(request.user, "role", None) in ["bank_manager", "bank_employee"])


class BankScopePermission(BasePermission):

    def has_object_permission(self, request, view, obj):
        user = request.user

        if request.user.is_superuser or request.user.is_staff or getattr(user, "role", None) == "admin":
            return True

        user_bank = getattr(user, "bank", None)
        if user_bank is None and hasattr(user, "profile"):
            user_bank = getattr(user.profile, "bank", None)

        if getattr(user, "role", None) in ["bank_manager", "bank_employee"]:
            return obj.bank_id == getattr(user_bank, "id", None)

        if getattr(user, "role", None) == "customer":
            return obj.customer_id == user.id

        return False

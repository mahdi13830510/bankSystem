from rest_framework.permissions import BasePermission


class IsAdminOrBankStaff(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and (
                getattr(user, "role", None) in ["admin", "bank_manager", "bank_employee"]
                or user.is_staff
                or user.is_superuser
            )
        )


class IsOwnerOrAdminOrBankStaff(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser or user.is_staff:
            return True
        if getattr(user, "role", None) in ["admin", "bank_manager", "bank_employee"]:
            return True
        return obj.customer_id == user.id

from rest_framework.permissions import BasePermission


class IsBankAdmin(BasePermission):

    def has_permission(self, request, view):
        return request.user.is_staff

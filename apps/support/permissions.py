from rest_framework.permissions import BasePermission

from apps.accounts.models import User
from apps.stores.permissions import is_platform_admin


class IsSupportStaff(BasePermission):
    message = "You do not have permission to manage support tickets."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if is_platform_admin(user):
            return True

        return user.role in {
            User.Role.STORE_MANAGER,
            User.Role.STAFF,
        }

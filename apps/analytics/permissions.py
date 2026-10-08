from rest_framework.permissions import BasePermission

from apps.accounts.models import User
from apps.stores.permissions import (
    get_managed_store_ids,
    is_platform_admin,
)


class IsAnalyticsStaff(BasePermission):
    message = "You do not have permission to view analytics."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if is_platform_admin(user):
            return True

        if user.role not in {
            User.Role.STORE_MANAGER,
            User.Role.STAFF,
        }:
            return False

        managed_store_ids = get_managed_store_ids(user)

        return bool(managed_store_ids)

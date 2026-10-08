from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import User

from .models import StoreStaffMembership


def is_platform_admin(user):
    return user.is_authenticated and (user.is_superuser or user.role == User.Role.ADMIN)


def get_managed_store_ids(user):
    """
    Return stores the authenticated employee
    is currently allowed to operate.
    """

    if not user.is_authenticated:
        return []

    if is_platform_admin(user):
        return None

    if user.role not in {
        User.Role.STORE_MANAGER,
        User.Role.STAFF,
    }:
        return []

    return list(
        StoreStaffMembership.objects.filter(
            user=user,
            is_active=True,
        ).values_list(
            "store_id",
            flat=True,
        )
    )


def ensure_store_access(
    user,
    store_id,
):
    """
    Platform admins can access every store.

    Store employees must have an active
    membership for the requested store.
    """

    if is_platform_admin(user):
        return

    allowed_store_ids = get_managed_store_ids(user)

    if store_id not in allowed_store_ids:
        raise PermissionDenied("You do not have permission " "to manage this store.")

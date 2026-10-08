from django.db import transaction

from .models import Notification


def create_notification(
    *,
    user,
    title,
    message,
    notification_type=(Notification.Type.GENERAL),
    data=None,
    send_push=True,
):
    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        data=data or {},
    )

    if send_push:
        notification_id = str(notification.id)

        transaction.on_commit(lambda: _queue_push_notification(notification_id))

    return notification


def _queue_push_notification(
    notification_id,
):
    # Local import prevents circular imports
    # between services.py and tasks.py.
    from .tasks import (
        send_push_notification,
    )

    send_push_notification.delay(notification_id)

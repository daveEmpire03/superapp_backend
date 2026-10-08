from celery import shared_task

from firebase_admin import messaging

from .firebase import send_fcm_message
from .models import (
    DeviceToken,
    Notification,
)


@shared_task(
    bind=True,
    autoretry_for=(
        RuntimeError,
        ConnectionError,
        TimeoutError,
    ),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def send_push_notification(
    self,
    notification_id,
):
    try:
        notification = Notification.objects.select_related("user").get(
            id=notification_id
        )

    except Notification.DoesNotExist:
        return {
            "status": "not_found",
            "notification_id": (str(notification_id)),
        }

    devices = list(
        DeviceToken.objects.filter(
            user=notification.user,
            is_active=True,
        )
    )

    if not devices:
        return {
            "status": "no_devices",
            "notification_id": (str(notification.id)),
            "sent": 0,
        }

    sent = 0
    deactivated = 0
    failed = 0

    for device in devices:
        try:
            send_fcm_message(
                token=device.token,
                title=notification.title,
                message=notification.message,
                data={
                    **notification.data,
                    "notification_id": (str(notification.id)),
                    "notification_type": (notification.notification_type),
                },
            )

            sent += 1

        except (
            messaging.UnregisteredError,
            messaging.SenderIdMismatchError,
        ):
            device.is_active = False

            device.save(
                update_fields=[
                    "is_active",
                    "updated_at",
                ]
            )

            deactivated += 1

        except messaging.FirebaseError:
            failed += 1

    return {
        "status": "processed",
        "notification_id": (str(notification.id)),
        "sent": sent,
        "deactivated": deactivated,
        "failed": failed,
    }

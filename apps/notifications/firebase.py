import os

import firebase_admin

from django.conf import settings
from firebase_admin import (
    credentials,
    messaging,
)


def get_firebase_app():
    try:
        return firebase_admin.get_app()

    except ValueError:
        credentials_path = getattr(
            settings,
            "FIREBASE_CREDENTIALS_PATH",
            "",
        )

        if not credentials_path:
            raise RuntimeError("FIREBASE_CREDENTIALS_PATH " "is not configured.")

        credentials_path = os.path.expanduser(credentials_path)

        if not os.path.isfile(credentials_path):
            raise RuntimeError("Firebase credentials file " "does not exist.")

        credential = credentials.Certificate(credentials_path)

        return firebase_admin.initialize_app(credential)


def send_fcm_message(
    *,
    token,
    title,
    message,
    data=None,
):
    app = get_firebase_app()

    payload = {
        str(key): str(value) for key, value in (data or {}).items() if value is not None
    }

    fcm_message = messaging.Message(
        token=token,
        notification=(
            messaging.Notification(
                title=title,
                body=message,
            )
        ),
        data=payload,
        android=messaging.AndroidConfig(
            priority="high",
        ),
        apns=messaging.APNSConfig(
            headers={
                "apns-priority": "10",
            },
            payload=messaging.APNSPayload(
                aps=messaging.Aps(
                    sound="default",
                ),
            ),
        ),
    )

    return messaging.send(
        fcm_message,
        app=app,
    )

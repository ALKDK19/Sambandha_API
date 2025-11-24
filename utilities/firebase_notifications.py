from typing import Any

from utilities.firebase import send_fcm_notification


def send_notification_to_user(user: Any, title: str, body: str, data: dict = None):
    """
    Sends a push notification to a single user via FCM.
    This is now a simple wrapper around the centralized utility.

    Args:
        user: The SQLAlchemy User object must have an `fcm_token`.
        title: The title of the notification.
        body: The main content of the notification.
        data: A dictionary of key-value pairs to send with the notification payload.
    """
    if not user.fcm_token:
        # We can still keep this check here for efficiency
        return

    send_fcm_notification(
        user_fcm_token=user.fcm_token,
        title=title,
        body=body,
        data=data
    )

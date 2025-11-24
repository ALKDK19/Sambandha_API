import logging
import traceback

import firebase_admin
from fastapi import HTTPException, status
from firebase_admin import credentials, auth as firebase_auth, messaging

from app.config import settings

logger = logging.getLogger(__name__)

initialized = False

CLOCK_SKEW_SECONDS = 5


def initialize_firebase_admin():
    try:
        global initialized
        if not initialized:
            cred = credentials.Certificate(settings.GOOGLE_APPLICATION_CREDENTIALS)
            project_id = getattr(cred, "project_id", None)
            init_options = {"projectId": project_id} if project_id else None
            firebase_admin.initialize_app(cred, init_options)
            initialized = True
            logger.info("Firebase Admin SDK initialized successfully. project_id=%s", project_id)
        else:
            logger.info("Firebase Admin SDK is already initialized.")
    except FileNotFoundError:
        logger.critical(
            "CRITICAL: Firebase service account key not found at `%s`. Firebase features will NOT work.",
            settings.GOOGLE_APPLICATION_CREDENTIALS,
        )
    except Exception as e:
        logger.critical("CRITICAL: Failed to initialize Firebase Admin SDK. Error: %s", e)


def verify_firebase_id_token(token: str) -> dict:
    global initialized
    if not initialized:
        logger.error("Firebase Admin SDK not initialized. Cannot verify token.")
        raise HTTPException(status_code=503, detail="Firebase service is not available.")

    if token and token.lower().startswith("bearer "):
        token = token.split(" ", 1)[1]

    if not token:
        logger.warning("Empty Firebase ID token received for verification.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Firebase ID token.")

    token_preview = token[:20] + "..." if len(token) > 20 else token
    logger.debug("Verifying Firebase ID token (preview=%s, length=%d)", token_preview, len(token))

    try:
        # primary verification (no revoke check). Allow a small clock skew to handle minor
        # server/client clock differences that can cause "Token used too early" errors.
        decoded_token = firebase_auth.verify_id_token(
            token, check_revoked=False, clock_skew_seconds=CLOCK_SKEW_SECONDS
        )
        logger.debug("Firebase token verified (check_revoked=False, clock_skew=%ss). uid=%s",
                     CLOCK_SKEW_SECONDS, decoded_token.get("uid") or decoded_token.get("user_id"))
        return decoded_token
    except Exception as e:
        # log full traceback and exception type for diagnostics
        tb = traceback.format_exc()
        logger.exception("Primary verify_id_token failed: %s\nTraceback:\n%s", type(e).__name__, tb)

        # Try a second verification attempt with explicit check_revoked=True to gather more info
        try:
            decoded_token = firebase_auth.verify_id_token(
                token, check_revoked=True, clock_skew_seconds=CLOCK_SKEW_SECONDS
            )
            logger.debug("Firebase token verified on second attempt (check_revoked=True, clock_skew=%ss). uid=%s",
                         CLOCK_SKEW_SECONDS, decoded_token.get("uid") or decoded_token.get("user_id"))
            return decoded_token
        except Exception as e2:
            tb2 = traceback.format_exc()
            logger.exception("Second verify_id_token (check_revoked=True) failed: %s\nTraceback:\n%s",
                             type(e2).__name__, tb2)

            # Map common firebase_admin exceptions to clearer HTTP messages with hints
            if isinstance(e2, firebase_auth.ExpiredIdTokenError):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Firebase ID token has expired.")
            if isinstance(e2, firebase_auth.RevokedIdTokenError):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                    detail="Firebase ID token has been revoked.")
            if isinstance(e2, firebase_auth.InvalidIdTokenError):
                # Add a hint: common causes: clock skew, inability to fetch public keys, or wrong credentials/project
                logger.error(
                    "Invalid token detected. Hints: check server clock, network access for key fetch, and that the "
                    "service account matches the client project.")
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Firebase ID token.")
            # Fallback
            raise HTTPException(status_code=500, detail="Could not verify Firebase token. See server logs for details.")


def send_fcm_notification(user_fcm_token: str, title: str, body: str, data: dict = None):
    """
    Sends a push notification to a single user's device via FCM.
    This function is called by `utilities.firebase_notifications`.

    - No-op if Firebase Admin SDK isn't initialized.
    - No-op if no token is provided.
    - Converts data values to strings because FCM requires string values.
    """
    global initialized
    if not initialized:
        logger.error("Firebase Admin SDK not initialized. Cannot send notification.")
        return

    if not user_fcm_token:
        logger.info("No FCM token provided. Skipping notification.")
        return

    # Ensure all data values are strings
    processed_data = {str(k): str(v) for k, v in (data or {}).items()}

    try:
        notification_payload = None
        if title and body:
            notification_payload = messaging.Notification(title=title, body=body)

        print("FCM PAYLOAD =====================================================")
        print("Title: ", title)
        print("Body: ", body)
        print("Data: ", processed_data)
        print("token: ", user_fcm_token)
        print("=================================================================")

        message = messaging.Message(
            notification=notification_payload,
            token=user_fcm_token,
            data=processed_data,
        )

        response = messaging.send(message)
        logger.info("Successfully sent FCM notification. Message ID: %s", response)
    except Exception as ex:
        logger.error("Failed to send FCM notification: %s", ex)

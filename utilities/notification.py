from sqlalchemy.orm import Session

from app.models.engagement import Notification


def send_profile_completion_notification(db: Session, user_id: int, percent: int, suggestions: list):
    if percent >= 80:
        return  # No notification needed if profile is sufficiently complete
    message = f"Your profile is {percent}% complete. Complete your profile for better matches! Suggestions: "
    message += ", ".join(suggestions[:3])  # Show top 3 suggestions
    notif = Notification(
        user_id=user_id,
        notification_type='profile_completion',
        title='Complete your profile for better matches',
        message_body=message,
        related_entity_type='profile',
        related_entity_id=user_id
    )
    db.add(notif)
    db.commit()


def send_profile_verification_status_notification(db: Session, user_id: int, status: str, message: str):
    notif = Notification(
        user_id=user_id,
        notification_type='profile_verification',
        title='Profile Verification Update',
        message_body=message,
        related_entity_type='profile',
        related_entity_id=user_id
    )
    db.add(notif)
    db.commit()


def send_new_match_notification(db: Session, user_id: int, matched_user_id: int):
    from app.models.user import User
    matched_user = db.query(User).filter(User.user_id == matched_user_id).first()
    # Only include username if the matched user exists and is active
    matched_username = matched_user.username if (matched_user and getattr(matched_user, 'is_active', False)) else "Someone"
    notif = Notification(
        user_id=user_id,
        notification_type='new_match',
        title='You have a new match!',
        message_body=f"You have matched with {matched_username}.",
        related_entity_type='match',
        related_entity_id=matched_user_id
    )
    db.add(notif)
    db.commit()

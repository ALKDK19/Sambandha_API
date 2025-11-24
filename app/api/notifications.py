from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.engagement import Notification
from app.schemas.engagement import NotificationInDB
from app.schemas.user import UserInDB
from utilities.security import get_current_user

router = APIRouter()


@router.get("/", response_model=List[NotificationInDB])
def get_notifications(
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db),
        limit: int = 10,
        offset: int = 0
):
    notifications = db.query(Notification).filter(
        Notification.user_id == current_user.user_id
    ).order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()
    return notifications


@router.patch("/{notification_id}/read")
def mark_notification_as_read(
        notification_id: int,
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    notification = db.query(Notification).filter(
        Notification.notification_id == notification_id,
        Notification.user_id == current_user.user_id
    ).first()

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.is_read = True
    db.commit()

    return {"message": "Notification marked as read"}

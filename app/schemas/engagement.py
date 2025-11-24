from datetime import datetime
from typing import Optional

from app.schemas.base import BaseSchema
from app.schemas.user import UserInDB


class NotificationBase(BaseSchema):
    user_id: int
    notification_type: str
    title: Optional[str] = None
    message_body: str
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[int] = None


class NotificationCreate(NotificationBase):
    pass


class NotificationInDB(NotificationBase):
    notification_id: int
    is_read: bool = False
    created_at: datetime


class RecommendationBase(BaseSchema):
    user_id: int
    recommended_user_id: int
    recommendation_score: float
    reason: Optional[str] = None
    status: str = "active"


class RecommendationCreate(RecommendationBase):
    pass


class RecommendationInDB(RecommendationBase):
    recommendation_id: int
    generated_at: datetime


class RecommendationWithUsers(RecommendationInDB):
    user: UserInDB
    recommended_user: UserInDB

    class Config:
        from_attributes = True

from sqlalchemy import Boolean
from sqlalchemy import Column, Integer, Text, String, ForeignKey
from sqlalchemy import DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class Notification(Base):
    __tablename__ = "notifications"

    notification_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"))
    notification_type = Column(String)  # 'new_match', 'message_request', 'profile_like', etc.
    title = Column(String, nullable=True)
    message_body = Column(Text)
    related_entity_type = Column(String, nullable=True)  # 'user', 'match', 'chat'
    related_entity_id = Column(Integer, nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationship
    user = relationship("User", back_populates="notifications")

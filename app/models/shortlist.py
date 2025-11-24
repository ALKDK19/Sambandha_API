from sqlalchemy import Column, Integer, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.models.base import Base


class Shortlist(Base):
    __tablename__ = "shortlists"

    shortlist_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    shortlisted_user_id = Column(Integer, ForeignKey("users.user_id"))
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("now()"))

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    shortlisted_user = relationship("User", foreign_keys=[shortlisted_user_id])

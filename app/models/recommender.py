# ...existing code...
from sqlalchemy import Column, Integer, ForeignKey, DateTime, String, Float, Text
from sqlalchemy.orm import relationship
from app.models.base import Base


class Recommendation(Base):
    __tablename__ = "recommendations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    recommended_user_id = Column(Integer, ForeignKey("users.user_id"))
    recommendation_score = Column(Float)
    reason = Column(Text, nullable=True)
    status = Column(String, default="pending")
    created_at = Column(DateTime)
    # relationships
    user = relationship("User", foreign_keys=[user_id])
    recommended_user = relationship("User", foreign_keys=[recommended_user_id])

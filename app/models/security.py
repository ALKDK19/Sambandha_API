from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.models.base import Base


class Report(Base):
    __tablename__ = "reports"

    report_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    reporter_user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"))
    reported_user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=True)  # Nullable for system reports
    report_reason_text = Column(String, nullable=True)
    report_details = Column(Text, nullable=True)
    report_category = Column(String, nullable=True)
    status = Column(String, default='pending_review')
    admin_id_assigned = Column(Integer, ForeignKey("admin.admin_id"), nullable=True)
    admin_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    reporter = relationship("User", foreign_keys=[reporter_user_id], back_populates="reported_users")
    reported = relationship("User", foreign_keys=[reported_user_id], back_populates="reports_against")


class BlockedUser(Base):
    __tablename__ = "blocked_users"

    block_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    blocker_user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"))
    blocked_user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"))
    reason = Column(String, nullable=True)
    created_at = Column(DateTime)

    # Relationships
    blocker = relationship("User", foreign_keys=[blocker_user_id], back_populates="blocked_users")
    blocked = relationship("User", foreign_keys=[blocked_user_id], back_populates="blocked_by")

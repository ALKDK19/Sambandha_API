from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from app.models.base import Base


class StaticContent(Base):
    __tablename__ = "static_content"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    key = Column(String, unique=True, nullable=False)  # e.g. 'about_us', 'terms', 'privacy_policy', 'faq'
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Announcement(Base):
    __tablename__ = "announcements"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

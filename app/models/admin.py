from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP
from sqlalchemy.sql import text

from app.models.base import Base


class Admin(Base):
    __tablename__ = "admin"

    admin_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, unique=True)
    password_hash = Column(String)
    email = Column(String, unique=True)
    full_name = Column(String)
    is_superuser = Column(Boolean, default=False, nullable=False)
    last_login = Column(TIMESTAMP(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("now()"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=text("now()"), onupdate=text("now()"))

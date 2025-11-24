from datetime import datetime, UTC

from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, text
from sqlalchemy.orm import relationship

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=True)
    phone_number = Column(String, unique=True, nullable=True)
    password_hash = Column(String)
    fcm_token = Column(String, nullable=True, index=True)  # It's good to index for faster lookups
    auth_provider = Column(String)
    is_phone_verified = Column(Boolean, default=False)
    is_email_verified = Column(Boolean, default=False)
    preferred_language = Column(String, default='en_US')
    deactivated_by = Column(String, default='None', nullable=True)
    theme_preference = Column(String, default='light')
    is_active = Column(Boolean, default=True)
    is_blocked = Column(Boolean, default=False)

    # Add server_default and onupdate to these columns in the model
    # This tells SQLAlchemy that the database is responsible for these values.
    created_at = Column(DateTime(timezone=True), server_default=text('now()'))
    updated_at = Column(DateTime(timezone=True), server_default=text('now()'), onupdate=text('now()'))

    # Relationships
    profile = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    preferences = relationship("Preference", back_populates="user", uselist=False, cascade="all, delete-orphan")
    sent_likes = relationship("Like", foreign_keys="Like.liker_user_id", back_populates="liker",
                              cascade="all, delete-orphan")
    received_likes = relationship("Like", foreign_keys="Like.liked_user_id", back_populates="liked",
                                  cascade="all, delete-orphan")
    matches_as_user1 = relationship("Match", foreign_keys="Match.user1_id", back_populates="user1",
                                    cascade="all, delete-orphan")
    matches_as_user2 = relationship("Match", foreign_keys="Match.user2_id", back_populates="user2",
                                    cascade="all, delete-orphan")
    sent_messages = relationship("Message", foreign_keys="Message.sender_user_id", back_populates="sender",
                                 cascade="all, delete-orphan")
    received_messages = relationship("Message", foreign_keys="Message.receiver_user_id", back_populates="receiver",
                                     cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", foreign_keys="Recommendation.user_id", back_populates="user",
                                   cascade="all, delete-orphan")
    reported_users = relationship("Report", foreign_keys="Report.reporter_user_id", back_populates="reporter",
                                  cascade="all, delete-orphan")
    reports_against = relationship("Report", foreign_keys="Report.reported_user_id", back_populates="reported",
                                   cascade="all, delete-orphan")
    blocked_users = relationship("BlockedUser", foreign_keys="BlockedUser.blocker_user_id", back_populates="blocker",
                                 cascade="all, delete-orphan")
    blocked_by = relationship("BlockedUser", foreign_keys="BlockedUser.blocked_user_id", back_populates="blocked",
                              cascade="all, delete-orphan")


class PhoneOTP(Base):
    __tablename__ = "phone_otps"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    phone_number = Column(String, index=True)
    otp_code = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    is_used = Column(Boolean, default=False)


class PendingRegistration(Base):
    __tablename__ = "pending_registrations"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, nullable=True)
    phone_number = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    otp_code = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    is_used = Column(Boolean, default=False)


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"))
    token = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    is_used = Column(Boolean, default=False)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    token = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_used = Column(Boolean, default=False)

    user = relationship("User")


class PasswordResetOtp(Base):
    __tablename__ = "password_reset_otps"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    otp_hash = Column(String, nullable=False)  # We will store a hash of the OTP
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_used = Column(Boolean, default=False)

    user = relationship("User")

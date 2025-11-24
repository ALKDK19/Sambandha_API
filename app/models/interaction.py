from sqlalchemy import Column, Integer, String, Float, ForeignKey, TIMESTAMP, Text
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.models.base import Base


class Like(Base):
    __tablename__ = "likes"

    like_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    liker_user_id = Column(Integer, ForeignKey("users.user_id"))
    liked_user_id = Column(Integer, ForeignKey("users.user_id"))
    like_type = Column(String, default='like')  # 'like', 'super_like', 'dislike'
    status = Column(String, default='active')  # 'active', 'disliked'
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("now()"))

    # Relationships
    liker = relationship("User", foreign_keys=[liker_user_id], back_populates="sent_likes")
    liked = relationship("User", foreign_keys=[liked_user_id], back_populates="received_likes")


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint('user1_id', 'user2_id', name='uq_match_user_pair'),
    )

    match_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user1_id = Column(Integer, ForeignKey("users.user_id"))
    user2_id = Column(Integer, ForeignKey("users.user_id"))
    compatibility_score = Column(Float, nullable=True)
    match_type = Column(String, default='score_only', server_default=text("'score_only'"))  # 'mutual_super_like',
    # 'mutual_like_and_score', 'score_only'
    match_status = Column(String, default='active')  # 'active', 'unmatched'
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("now()"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=text("now()"), onupdate=text("now()"))

    # Relationships
    user1 = relationship("User", foreign_keys=[user1_id], back_populates="matches_as_user1")
    user2 = relationship("User", foreign_keys=[user2_id], back_populates="matches_as_user2")
    chats = relationship("Chat", back_populates="match")


class ProfileVisit(Base):
    __tablename__ = "profile_visits"

    visit_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    visitor_user_id = Column(Integer, ForeignKey("users.user_id"))
    visited_profile_user_id = Column(Integer, ForeignKey("users.user_id"))
    visit_timestamp = Column(TIMESTAMP(timezone=True), server_default=text("now()"))


class Chat(Base):
    __tablename__ = "chats"

    chat_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    match_id = Column(Integer, ForeignKey("matches.match_id"), nullable=True)
    initiator_user_id = Column(Integer, ForeignKey("users.user_id"))
    receiver_user_id = Column(Integer, ForeignKey("users.user_id"))
    state = Column(String, default='request')  # 'request', 'active'
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("now()"))

    # Relationships
    match = relationship("Match", back_populates="chats")
    messages = relationship("Message", back_populates="chat")
    initiator = relationship("User", foreign_keys=[initiator_user_id])
    receiver = relationship("User", foreign_keys=[receiver_user_id])


class Message(Base):
    __tablename__ = "messages"

    message_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    chat_id = Column(Integer, ForeignKey("chats.chat_id"))
    sender_user_id = Column(Integer, ForeignKey("users.user_id"))
    receiver_user_id = Column(Integer, ForeignKey("users.user_id"))
    message_content = Column(Text)
    message_type = Column(String, default='text')  # 'text', 'image_url_in_message', 'intro_request'
    sent_at = Column(TIMESTAMP(timezone=True), server_default=text("now()"))
    read_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # Relationships
    chat = relationship("Chat", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_user_id], back_populates="sent_messages")
    receiver = relationship("User", foreign_keys=[receiver_user_id], back_populates="received_messages")

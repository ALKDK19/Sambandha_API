from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.base import BaseSchema
from app.schemas.profile import ProfileSummary, ProfileInDB
from app.schemas.user import UserInDB


class LikeBase(BaseSchema):
    # liker_user_id: int
    liked_user_id: int
    like_type: str = "like"


class LikeCreate(LikeBase):
    is_not_interested: Optional[bool] = False


class LikeInDB(LikeBase):
    like_id: int
    status: str = "active"
    created_at: datetime


class LikeWithUser(LikeInDB):
    liker: UserInDB
    liked: UserInDB


class MatchBase(BaseSchema):
    user1_id: int
    user2_id: int
    compatibility_score: Optional[float] = None
    match_status: str = "active"
    match_type: str = "score_only"


class MatchCreate(MatchBase):
    pass


class MatchInDB(MatchBase):
    match_id: int
    created_at: datetime
    updated_at: datetime


class MatchWithUsers(MatchInDB):
    user1: ProfileSummary
    user2: ProfileSummary


class ProfileVisitBase(BaseSchema):
    visitor_user_id: int
    visited_profile_user_id: int


class ProfileVisitCreate(ProfileVisitBase):
    pass


class ProfileVisitInDB(ProfileVisitBase):
    visit_id: int
    visit_timestamp: datetime


class ChatBase(BaseSchema):
    match_id: Optional[int] = None
    initiator_user_id: int
    receiver_user_id: int
    state: str = "request"  # 'request', 'active'


class ChatCreate(ChatBase):
    pass


class ChatInDB(ChatBase):
    chat_id: int
    created_at: datetime


class ChatWithUsers(ChatInDB):
    users: list[ProfileInDB] = []
    match: Optional[MatchInDB] = None


class MessageBase(BaseModel):
    message_content: str
    message_type: str = "text"

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    receiver_user_id: int
    message_content: str
    message_type: str = "text"

    class Config:
        from_attributes = True


class MessageInDB(MessageBase):
    message_id: int
    sent_at: datetime
    read_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MessageInResponse(BaseModel):
    message_id: int
    chat_id: int
    sender_user_id: int
    receiver_user_id: int
    message_content: str
    message_type: str = "text"
    sent_at: datetime
    read_at: Optional[datetime] = None


class MessageWithUsers(MessageInDB):
    sender: UserInDB
    receiver: UserInDB
    chat: ChatInDB

    class Config:
        from_attributes = True


class LikeReceivedResponse(BaseModel):
    liker_profile: ProfileSummary
    like_type: str

    class Config:
        from_attributes = True

# class MatchInDB(BaseModel):
#     id: int
#     user_id: int
#     matched_user_id: int
#     created_at: datetime
#     status: str
#     is_audit: bool
#
#     class Config:
#         orm_mode = True

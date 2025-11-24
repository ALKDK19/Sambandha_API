from datetime import datetime
from typing import Optional

from app.schemas.base import BaseSchema
from app.schemas.user import UserInDB


class ReportBase(BaseSchema):
    reporter_user_id: int
    reported_user_id: Optional[int] = None  # Optional for system reports
    report_reason_text: Optional[str] = None
    report_details: Optional[str] = None
    report_category: Optional[str] = None


class ReportCreate(BaseSchema):
    reported_user_id: Optional[int] = None
    report_category: Optional[str] = None
    report_details: Optional[str] = None
    report_reason_text: Optional[str] = None


class ReportInDB(ReportBase):
    report_id: int
    status: str = "pending_review"
    admin_id_assigned: Optional[int] = None
    admin_notes: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None


class ReportWithUsers(ReportInDB):
    reporter: Optional[UserInDB]
    reported: Optional[UserInDB]


class BlockedUserBase(BaseSchema):
    blocker_user_id: int
    blocked_user_id: int


class BlockedUserCreate(BlockedUserBase):
    pass


class BlockedUserInDB(BlockedUserBase):
    block_id: int
    created_at: datetime

    class Config:
        orm_mode = True


class BlockedUserWithUsers(BlockedUserInDB):
    blocker: UserInDB
    blocked: UserInDB

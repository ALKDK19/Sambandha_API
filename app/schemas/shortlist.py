from datetime import datetime

from app.schemas.base import BaseSchema


class ShortlistBase(BaseSchema):
    shortlisted_user_id: int


class ShortlistCreate(ShortlistBase):
    pass


class ShortlistInDB(ShortlistBase):
    user_id: int
    shortlist_id: int
    created_at: datetime

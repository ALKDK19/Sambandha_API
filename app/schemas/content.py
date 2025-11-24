from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class StaticContentBase(BaseModel):
    key: str
    title: str
    content: str

class StaticContentCreate(StaticContentBase):
    pass

class StaticContentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

class StaticContentInDB(StaticContentBase):
    id: int
    updated_at: datetime
    class Config:
        from_attributes = True

class AnnouncementBase(BaseModel):
    title: str
    message: str

class AnnouncementCreate(AnnouncementBase):
    pass

class AnnouncementUpdate(BaseModel):
    title: Optional[str] = None
    message: Optional[str] = None

class AnnouncementInDB(AnnouncementBase):
    id: int
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True


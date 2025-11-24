from typing import Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime

from app.schemas.base import BaseSchema

class AdminBase(BaseSchema):
    username: str
    email: EmailStr
    full_name: str

class AdminCreate(AdminBase):
    password: str

class AdminUpdate(AdminBase):
    password: Optional[str] = None

class AdminInDB(AdminBase):
    admin_id: int
    is_active: bool = True
    is_superuser: bool  # Add this field
    last_login: Optional[datetime] = None
    created_at: datetime

# New schema for updating other admins by superuser
class AdminUpdateBySuperuser(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None  # To allow password resets

class AdminLogin(BaseModel):
    username: str
    password: str

class AdminToken(BaseModel):
    access_token: str
    token_type: str
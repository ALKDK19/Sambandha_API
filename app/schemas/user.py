import re
from datetime import datetime
from typing import Optional

from pydantic import EmailStr, BaseModel, field_validator, validator

from app.schemas.base import BaseSchema


class UserBase(BaseSchema):
    username: str
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    auth_provider: Optional[str] = None
    preferred_language: Optional[str] = "en_US"
    theme_preference: Optional[str] = "light"
    is_active: Optional[bool] = True
    is_blocked: Optional[bool] = False
    deactivated_by: Optional[str] = "None"

    @field_validator("phone_number")
    def validate_phone_number(cls, v):
        if v is not None:
            # Example: 10-15 digits, can be customized
            if not re.fullmatch(r"\+?\d{9,15}", v):
                raise ValueError("Invalid phone number format.")
        return v

    @field_validator("email")
    def validate_email(cls, v):
        # EmailStr already validates, but you can add custom logic if needed
        return v


class UserCreate(UserBase):
    password: str

    @field_validator("password")
    def validate_password(cls, v):
        # Example: at least 8 chars, 1 uppercase, 1 lowercase, 1 digit, 1 special char
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if len(v) > 72:
            raise ValueError("Password cannot be longer than 72 characters.")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit.")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character.")
        return v


class RegisterWithFirebase(UserCreate):
    """
    Inherits username, email, and password (with its validation) from UserCreate.
    We just add the token_id field.
    """
    token_id: str


class UserUpdate(UserBase):
    password: Optional[str] = None


class UserInDB(UserBase):
    user_id: int
    is_phone_verified: bool = False
    is_email_verified: bool = False
    is_active: bool = True
    is_blocked: bool = False
    deactivated_by: Optional[str] = "None"
    created_at: datetime
    updated_at: datetime


class UserLogin(BaseModel):
    email_or_phone: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: Optional[int] = None


class FcmTokenUpdate(BaseModel):
    """
    Schema for receiving the FCM token from the client.
    """
    fcm_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordWithOtpRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str

    @validator("new_password")
    def validate_password(cls, v):
        # Example: at least 8 chars, 1 uppercase, 1 lowercase, 1 digit, 1 special char
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if len(v) > 72:
            raise ValueError("Password cannot be longer than 72 characters.")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit.")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character.")
        return v


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @validator("new_password")
    def validate_new_password(cls, v):
        # Re-using the same strong password validation
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if len(v) > 72:
            raise ValueError("Password cannot be longer than 72 characters.")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        if not any(c in "!@#$%^&*(),.?\":{}|<>" for c in v):
            raise ValueError("Password must contain at least one special character.")
        return v

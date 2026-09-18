from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.admin import Admin
from app.models.user import User
from app.schemas.user import TokenData

# OAuth2 schemes
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")
# Optional oauth2 scheme for endpoints that should work for both guests and authenticated users
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)
admin_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/admin/login")


# --------------------------
# Common Security Functions
# --------------------------

def verify_password(plain_password: str, hashed_password: str) -> bool:
    plain_bytes = plain_password.encode("utf-8")[:72]
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(plain_bytes, hashed_bytes)


def get_password_hash(password: str) -> str:
    # Truncate password to 72 bytes for bcrypt
    password_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


# OTP hash and verify functions using bcrypt

def get_otp_hash(otp: str) -> str:
    otp_bytes = otp.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(otp_bytes, salt).decode("utf-8")


def verify_otp(plain_otp: str, hashed_otp: str) -> bool:
    plain_bytes = plain_otp.encode("utf-8")[:72]
    hashed_bytes = hashed_otp.encode("utf-8")
    return bcrypt.checkpw(plain_bytes, hashed_bytes)


# --------------------------
# User Authentication
# --------------------------

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id)
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.user_id == token_data.user_id).first()
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
        current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_optional_current_user(
        token: str = Depends(oauth2_scheme_optional),
        db: Session = Depends(get_db)
) -> User | None:
    """Return the user if a valid bearer token is provided, otherwise None.
    This is a non-strict variant of `get_current_user` suitable for endpoints that
    are usable by both guests and authenticated users.
    """
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            return None
    except JWTError:
        return None
    user = db.query(User).filter(User.user_id == user_id).first()
    return user


# --------------------------
# Active-user helpers
# --------------------------

def active_user_ids_query(db: Session):
    """Return an SQLAlchemy query that yields user IDs for users marked active.
    Use this in Profile queries to avoid loading all IDs into memory.
    Example: query = query.filter(Profile.user_id.in_(active_user_ids_query(db)))

    IMPORTANT: avoid using Python identity checks (e.g. `is True`) here because that
    is evaluated in Python and can lead to queries like `WHERE false`. Use SQLAlchemy
    comparison operators so the expression is compiled into proper SQL.
    """
    # Use SQLAlchemy boolean comparison rather than Python `is` to produce a valid SQL predicate
    # Return an explicit subquery so callers can safely use `.in_(...)` with it.
    return db.query(User.user_id).filter(User.is_active == True).subquery()


def ensure_active_user_or_404(user: User):
    """Raise a 404 if the user is None or inactive. Returns the user when active."""
    if user is None or not getattr(user, 'is_active', True):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


# --------------------------
# Admin Authentication
# --------------------------

def create_admin_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.ADMIN_SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def get_current_admin(
        token: str = Depends(admin_oauth2_scheme),
        db: Session = Depends(get_db)
) -> Admin:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate admin credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.ADMIN_SECRET_KEY, algorithms=[settings.ALGORITHM])
        admin_id: int = payload.get("admin_id")
        if admin_id is None:
            raise credentials_exception
        token_data = {"admin_id": admin_id}
    except JWTError:
        raise credentials_exception

    admin = db.query(Admin).filter(Admin.admin_id == token_data["admin_id"]).first()
    if admin is None:
        raise credentials_exception

    return admin


async def get_current_active_admin(
        current_admin: Admin = Depends(get_current_admin)
) -> Admin:
    if not current_admin.is_active:
        raise HTTPException(status_code=400, detail="Inactive admin account")
    return current_admin


# --------------------------
# Password Verification
# --------------------------

def verify_admin_password(plain_password: str, hashed_password: str) -> bool:
    return verify_password(plain_password, hashed_password)


def get_admin_password_hash(password: str) -> str:
    return get_password_hash(password)


async def get_current_superuser(
        current_admin: Admin = Depends(get_current_active_admin)
) -> Admin:
    if not current_admin.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action."
        )
    return current_admin

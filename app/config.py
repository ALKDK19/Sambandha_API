from typing import List, Optional

from pydantic import EmailStr, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PYTHON_VERSION: str = "3.11"
    DEBUG: bool = False

    ALLOWED_ORIGINS: List[str] = ["http://localhost:8080"]
    ADMIN_ALLOWED_ORIGINS: List[str] = []  # <-- added: separate admin origins
    SECRET_KEY: Optional[str] = None
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ADMIN_SECRET_KEY: Optional[str] = None
    ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    DATABASE_URL: Optional[str] = None
    FIRST_ADMIN_USERNAME: Optional[str] = None
    FIRST_ADMIN_EMAIL: Optional[EmailStr] = None
    FIRST_ADMIN_FULL_NAME: Optional[str] = "Sambandha Admin"
    FIRST_ADMIN_PASSWORD: Optional[str] = None

    SMTP_SERVER: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USERNAME: Optional[EmailStr] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: Optional[EmailStr] = None

    GOOGLE_APPLICATION_CREDENTIALS: str = ""

    CLOUDINARY_CLOUD_NAME: Optional[str] = None
    CLOUDINARY_API_KEY: Optional[str] = None
    CLOUDINARY_API_SECRET: Optional[str] = None

    @field_validator("SECRET_KEY", "ADMIN_SECRET_KEY")
    def validate_secret_keys(cls, v):
        if v is not None and len(v) < 32:
            raise ValueError("Secret keys must be at least 32 characters long")
        return v

    @field_validator("DATABASE_URL")
    def validate_database_url(cls, v):
        if v is not None and not v.startswith(("postgresql://", "sqlite://", "mysql://")):
            raise ValueError("Invalid database URL format")
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

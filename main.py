from contextlib import asynccontextmanager
from datetime import datetime, UTC

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    auth, users, profiles, preferences,
    likes, matches, chats, messages,
    notifications, admin, shortlist, contents, security
)
from app.config import settings
from app.database import engine, SessionLocal
from app.models.admin import Admin
from app.models.base import Base
from utilities.cloudinary import configure_cloudinary
from utilities.recsys.embedding_utils import warmup_embeddings_on_startup
from utilities.firebase import initialize_firebase_admin
from utilities.logging_config import logger
from utilities.security import get_admin_password_hash


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Sambandha API starting up...")
    initialize_firebase_admin()
    configure_cloudinary()
    seed_first_admin()

    # ✅ Run automatic embedding warmup
    db = None

    try:
        db = SessionLocal()
        warmup_embeddings_on_startup(db)
    except Exception as e:
        logger.error(f"❌ Failed during embedding warmup: {e}")
    finally:
        db.close()

    yield
    logger.info("Sambandha API shutting down...")


app = FastAPI(
    title="Sambandha API",
    version="1.0.0",
    description="Backend API for Sambandha - Nepali Matrimonial App",
    docs_url="/api/docs" if settings.DEBUG else None,  # Hide docs in production
    redoc_url="/api/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# Setup CORS
allowed_origins = list(settings.ALLOWED_ORIGINS or [])
# include admin-specific origins if set
if getattr(settings, "ADMIN_ALLOWED_ORIGINS", None):
    for o in settings.ADMIN_ALLOWED_ORIGINS:
        if o not in allowed_origins:
            allowed_origins.append(o)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# create database tables if they do not exist
logger.warning("Creating database tables if they do not exist...")
Base.metadata.create_all(bind=engine)

# Include API routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(profiles.router, prefix="/api/profiles", tags=["Profiles"])
app.include_router(preferences.router, prefix="/api/preferences", tags=["Preferences"])
app.include_router(likes.router, prefix="/api/likes", tags=["Likes & Matches"])
app.include_router(matches.router, prefix="/api/matches", tags=["Likes & Matches"])
app.include_router(chats.router, prefix="/api/chats", tags=["Messaging"])
app.include_router(messages.router, prefix="/api/messages", tags=["Messaging"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(shortlist.router, prefix="/api/shortlist", tags=["Shortlist"])
app.include_router(contents.router, prefix="/api/contents", tags=["Content"])
app.include_router(security.router, prefix="/api/security", tags=["Security"])


# Health check endpoint
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "version": "1.0.0"
    }


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to Sambandha API",
        "docs": "/api/docs",
        "redoc": "/api/redoc"
    }


def seed_first_admin():
    # Only proceed if the environment variables are set
    if not all([settings.FIRST_ADMIN_USERNAME, settings.FIRST_ADMIN_EMAIL, settings.FIRST_ADMIN_PASSWORD]):
        logger.info("First admin environment variables not set. Skipping admin seeding.")
        return

    db = SessionLocal()
    try:
        # Check if an admin already exists
        existing_admin = db.query(Admin).first()
        if existing_admin:
            logger.info("Admin user already exists. Skipping seeding.")
            return

        # Create the first admin
        hashed_password = get_admin_password_hash(settings.FIRST_ADMIN_PASSWORD)
        new_admin = Admin(
            username=settings.FIRST_ADMIN_USERNAME,
            email=settings.FIRST_ADMIN_EMAIL,
            full_name=settings.FIRST_ADMIN_FULL_NAME,
            password_hash=hashed_password,
            is_active=True,
            is_superuser=True  # Set this for the first admin
        )
        db.add(new_admin)
        db.commit()
        logger.info(f"Successfully seeded first admin user: {settings.FIRST_ADMIN_USERNAME}")
    except Exception as e:
        logger.error(f"Error seeding first admin: {e}")
        db.rollback()
    finally:
        db.close()

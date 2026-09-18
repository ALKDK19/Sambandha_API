"""
Seeder 001: Create the initial admin user if not present.

This is idempotent and safe to run multiple times.
"""
from app.models.admin import Admin
from app.config import settings
from utilities.logging_config import logger
from utilities.security import get_admin_password_hash


def seed(db):
    """Idempotent seeding: creates the first admin if no admin exists and env vars are set."""
    # Only proceed if the environment variables are set
    if not all([settings.FIRST_ADMIN_USERNAME, settings.FIRST_ADMIN_EMAIL, settings.FIRST_ADMIN_PASSWORD]):
        logger.info("First admin environment variables not set. Skipping admin seeding.")
        return

    existing = db.query(Admin).first()
    if existing:
        logger.info("Admin user already exists. Skipping seeding.")
        return

    hashed_password = get_admin_password_hash(settings.FIRST_ADMIN_PASSWORD)
    new_admin = Admin()
    # Assign fields explicitly to match SQLAlchemy column names
    new_admin.username = settings.FIRST_ADMIN_USERNAME
    new_admin.email = settings.FIRST_ADMIN_EMAIL
    new_admin.full_name = settings.FIRST_ADMIN_FULL_NAME
    new_admin.password_hash = hashed_password
    new_admin.is_active = True
    new_admin.is_superuser = True
    db.add(new_admin)
    logger.info(f"Seeded first admin: {settings.FIRST_ADMIN_USERNAME}")

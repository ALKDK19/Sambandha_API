from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import settings

DATABASE_URL = str(settings.DATABASE_URL)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Enables connection health checks
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_size=5,  # Maximum pool size
    max_overflow=10  # Maximum overflow connections
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

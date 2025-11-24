from sqlalchemy import Column, String, Integer, Date, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import LargeBinary

from app.models.base import Base


class Profile(Base):
    __tablename__ = "profiles"

    profile_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), unique=True)

    # Personal Information
    first_name = Column(String)
    last_name = Column(String)
    date_of_birth = Column(Date)
    gender = Column(String)  # 'male', 'female', 'other'
    bio = Column(Text, nullable=True)
    height_cm = Column(Integer, nullable=True)
    marital_status = Column(String, nullable=True)

    # Location
    address = Column(Text, nullable=True)
    city_text = Column(String, nullable=True)
    country = Column(String, default='Nepal')

    # Education & Profession
    education_level_text = Column(String, nullable=True)
    education_field_text = Column(String, nullable=True)
    profession_text = Column(String, nullable=True)
    annual_salary_npr = Column(Integer, nullable=True)

    # Lifestyle & Preferences
    religion_text = Column(String, nullable=True)
    caste_text = Column(String, nullable=True)
    mother_tongue = Column(String, nullable=True)
    dietary_preferences = Column(String, nullable=True)
    smoking_habits = Column(String, nullable=True)
    drinking_habits = Column(String, nullable=True)
    hobbies_interests = Column(Text, nullable=True)

    # family information
    family_status = Column(String, nullable=True)
    family_type = Column(String, nullable=True)

    # Horoscope Details
    rashi = Column(String, nullable=True)
    nakshatra = Column(String, nullable=True)
    gotra = Column(String, nullable=True)
    manglik_status = Column(String, nullable=True)
    birth_time = Column(String, nullable=True)
    birth_place = Column(String, nullable=True)
    kundali_image_url = Column(String, nullable=True)

    # Profile Media
    primary_profile_image_url = Column(String, nullable=True)
    additional_multiple_images = Column(JSON, nullable=True)  # stores a list of image URLs
    video_intro_url = Column(String, nullable=True)

    # Embedding vector (serialized bytes)
    embedding_vector = Column(LargeBinary, nullable=True)

    # Profile Status
    profile_completion_percentage = Column(Integer, default=0)
    profile_visibility = Column(String, default='public')
    last_active = Column(String, nullable=True)

    # Verification
    government_id_url = Column(String, nullable=True)
    is_verified = Column(Integer, default=0)  # 0 = not verified, 1 = verified
    verified_at = Column(Date, nullable=True)
    verified_by_admin_id = Column(Integer, ForeignKey("admin.admin_id"), nullable=True)
    verification_status = Column(String, default="unverified")  # unverified, requested, verified, canceled

    # Admin/Moderation fields
    is_approved = Column(Integer, default=0)  # 0: not approved, 1: approved
    is_hidden = Column(Integer, default=0)  # 0: visible, 1: hidden
    photo_url = Column(String, nullable=True)  # Main profile photo URL

    # Relationships
    user = relationship("User", back_populates="profile")

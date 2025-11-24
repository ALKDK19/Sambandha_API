from datetime import date
from typing import Optional, List

from app.schemas.base import BaseSchema


class ProfileBase(BaseSchema):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    bio: Optional[str] = None
    height_cm: Optional[int] = None
    marital_status: Optional[str] = None

    # Location
    address: Optional[str] = None
    city_text: Optional[str] = None
    country: Optional[str] = "Nepal"

    # Education & Profession
    education_level_text: Optional[str] = None
    education_field_text: Optional[str] = None
    profession_text: Optional[str] = None
    annual_salary_npr: Optional[int] = None

    # religion and habits
    religion_text: Optional[str] = None
    caste_text: Optional[str] = None
    mother_tongue: Optional[str] = None
    dietary_preferences: Optional[str] = None
    smoking_habits: Optional[str] = None
    drinking_habits: Optional[str] = None
    hobbies_interests: Optional[str] = None

    # family information
    family_status: Optional[str] = None
    family_type: Optional[str] = None

    # horoscope details
    rashi: Optional[str] = None
    nakshatra: Optional[str] = None
    gotra: Optional[str] = None
    manglik_status: Optional[str] = None
    birth_time: Optional[str] = None
    birth_place: Optional[str] = None
    kundali_image_url: Optional[str] = None

    # Profile Media
    primary_profile_image_url: Optional[str] = None
    additional_multiple_images: Optional[List[str]] = None
    video_intro_url: Optional[str] = None
    government_id_url: Optional[str] = None


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(ProfileBase):
    pass


class ProfileInDB(ProfileBase):
    profile_id: int
    user_id: int
    government_id_url: Optional[str] = None
    is_verified: int = 0
    verified_at: Optional[date] = None
    verified_by_admin_id: Optional[int] = None
    profile_completion_percentage: int = 0
    verification_status: str = "unverified"

    # Badge property for frontend
    @property
    def verification_badge(self) -> bool:
        return self.is_verified == 1


class ProfileCompletionSuggestion(BaseSchema):
    completion_percentage: int
    missing_fields: List[str]
    suggestions: List[str]


class ProfileSummary(BaseSchema):
    user_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    bio: Optional[str] = None
    height_cm: Optional[int] = None
    marital_status: Optional[str] = None

    # Location
    address: Optional[str] = None
    city_text: Optional[str] = None
    country: Optional[str] = "Nepal"

    # Education & Profession
    education_level_text: Optional[str] = None
    college_name: Optional[str] = None
    profession_text: Optional[str] = None
    company_name: Optional[str] = None
    annual_salary_npr: Optional[int] = None

    # religion and habits
    religion_text: Optional[str] = None
    caste_text: Optional[str] = None
    mother_tongue: Optional[str] = None
    dietary_preferences: Optional[str] = None
    smoking_habits: Optional[str] = None
    drinking_habits: Optional[str] = None
    hobbies_interests: Optional[str] = None

    # horoscope details
    rashi: Optional[str] = None
    nakshatra: Optional[str] = None
    gotra: Optional[str] = None
    manglik_status: Optional[str] = None
    birth_time: Optional[str] = None
    birth_place: Optional[str] = None
    kundali_image_url: Optional[str] = None
    is_verified: int = 0
    primary_profile_image_url: Optional[str] = None
    additional_multiple_images: Optional[List[str]] = None
    video_intro_url: Optional[str] = None

    is_liked: Optional[bool] = None
    like_type: Optional[str] = None

    is_shortlisted: Optional[bool] = None

    # Badge property for frontend
    @property
    def verification_badge(self) -> bool:
        return self.is_verified == 1

    class Config:
        from_attributes = True

from typing import Optional

from app.schemas.base import BaseSchema


class PreferenceBase(BaseSchema):
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    min_height_cm: Optional[int] = None
    max_height_cm: Optional[int] = None
    preferred_marital_status_text: Optional[str] = None
    preferred_mother_tongue: Optional[str] = None
    preferred_religions_text: Optional[str] = None
    preferred_castes_text: Optional[str] = None
    preferred_family_type_text: Optional[str] = None
    preferred_education_levels_text: Optional[str] = None
    preferred_education_field_text: Optional[str] = None
    preferred_professions_text: Optional[str] = None
    preferred_smoking_habits: Optional[str] = None
    preferred_drinking_habits: Optional[str] = None
    preferred_dietary_habits: Optional[str] = None
    preferred_locations_text: Optional[str] = None
    preferred_manglik_status: Optional[str] = None
    min_salary_expectation: Optional[int] = None
    max_salary_expectation: Optional[int] = None
    # Canonical values are capitalized: 'Any', 'Male', 'Female', 'Other', or comma-separated like 'Male, Female'
    looking_for: Optional[str] = None  # e.g. 'Male', 'Female', 'Other', or comma-separated for multiple


class PreferenceCreate(PreferenceBase):
    pass


class PreferenceUpdate(PreferenceBase):
    pass


class PreferenceInDB(PreferenceBase):
    preference_id: int
    user_id: int

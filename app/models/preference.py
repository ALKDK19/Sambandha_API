from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base


class Preference(Base):
    __tablename__ = "preferences"

    preference_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), unique=True)

    # Age preferences
    min_age = Column(Integer, nullable=True)  # Any, (numeric value)
    max_age = Column(Integer, nullable=True)  # Any, (numeric value)

    # Physical preferences
    min_height_cm = Column(Integer, nullable=True)  # Any, (numeric value)
    max_height_cm = Column(Integer, nullable=True)  # Any, (numeric value)

    # Marital status preferences
    preferred_marital_status_text = Column(Text, nullable=True)  # Any, Single, Divorced, Widowed, (Comma-separated
    # values)

    # Mother tongue preferences
    preferred_mother_tongue = Column(String, nullable=True)  # Any, (single value), (Comma-separated values)

    # Family preferences
    preferred_family_type_text = Column(Text, nullable=True)  # Any, Joint, Nuclear

    # Religious preferences
    preferred_religions_text = Column(Text, nullable=True)  # Any, (single value), (Comma-separated values)
    preferred_castes_text = Column(Text, nullable=True)  # Any, (single value), (Comma-separated values)
    preferred_manglik_status = Column(String, nullable=True)  # Any, manglik, non-manglik

    # Education & Profession preferences
    preferred_education_levels_text = Column(Text, nullable=True)  # Any, (single value), (Comma-separated values)
    preferred_education_field_text = Column(Text, nullable=True)  # Any, (single value), (Comma-separated values)
    preferred_professions_text = Column(Text, nullable=True)  # Any, (single value), (Comma-separated values)

    # preferred diet preferences
    preferred_smoking_habits = Column(String, nullable=True)  # Any, Non-smoker, Occasional, Regular),
    # (Comma-separated values)
    preferred_drinking_habits = Column(String, nullable=True)  # Any, Non-drinker, Occasional, Regular),
    # (Comma-separated values)
    preferred_dietary_habits = Column(String, nullable=True)  # Any, Vegetarian, Non-Vegetarian), (Comma-separated
    # values)

    # Location preferences
    preferred_locations_text = Column(Text, nullable=True)  # Any, (single value), (Comma-separated values)

    # Financial preferences
    min_salary_expectation = Column(Integer, nullable=True)  # Any, (numeric value)
    max_salary_expectation = Column(Integer, nullable=True)  # Any, (numeric value)

    # Gender preference
    looking_for = Column(String, nullable=True)  # Any, Male, Female, Other

    # Relationship
    user = relationship("User", back_populates="preferences")

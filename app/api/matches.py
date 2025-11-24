import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.interaction import Match, Like
from app.models.preference import Preference
from app.models.profile import Profile
from app.schemas.profile import ProfileSummary
from app.schemas.user import UserInDB
from utilities.security import get_current_user, active_user_ids_query

router = APIRouter()

# ---------------------------------------------------------
# 1. ROBUST HELPER FUNCTIONS
# ---------------------------------------------------------

def _split_and_normalize(pref_value: str | None) -> list[str]:
    """Split, lower, strip, and dedupe comma-separated strings."""
    if not pref_value:
        return []
    parts = [p.strip() for p in pref_value.split(',') if p.strip()]
    lowered = [p.lower() for p in parts]
    if 'any' in lowered:
        return []
    # dedupe while preserving order
    seen = set()
    out = []
    for v in lowered:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


def _apply_in_filter(query, column, pref_value: str | None):
    """Apply a case-insensitive IN filter."""
    items = _split_and_normalize(pref_value)
    if not items:
        return query
    return query.filter(func.lower(column).in_(items))


def _apply_address_like_filter(query, column, pref_value: str | None):
    """Apply partial matching for locations (OR logic)."""
    items = _split_and_normalize(pref_value)
    if not items:
        return query
    clauses = [func.lower(column).contains(item) for item in items]
    return query.filter(or_(*clauses))


def _looking_for_to_genders_local(looking_for: str | None, fallback_gender: str | None = None) -> list[str]:
    """Map 'Bride', 'Groom', etc. to 'male', 'female'."""
    if not looking_for:
        return [fallback_gender] if fallback_gender else []

    tokens = _split_and_normalize(looking_for)
    targets = set()

    for p in tokens:
        if p == 'any':
            return []
        if p in ['male', 'groom', 'bridegroom']:
            targets.add('male')
        elif p in ['female', 'bride']:
            targets.add('female')
        elif p == 'other':
            targets.add('other')

    if not targets and fallback_gender:
        return [fallback_gender]
    return list(targets)


def _apply_filter_safely(current_query, column, pref_value, filter_name):
    """
    Applies a filter ONLY if it results in > 0 matches.
    Otherwise, skips the filter to preserve previous results.
    WARNING: Executes a DB Query (count) every time it is called.
    """
    # 1. Attempt to apply the standard filter
    candidate_query = _apply_in_filter(current_query, column, pref_value)

    # 2. Optimization: If pref_value was empty, query didn't change. Return early.
    if str(candidate_query) == str(current_query):
        return current_query

    # 3. EXECUTE COUNT (Performance Hit Here)
    count = candidate_query.count()

    if count > 0:
        # print(f"  [Filter] {filter_name}: Applied. (Remaining: {count})") # Uncomment for debug
        return candidate_query
    else:
        # print(f"  [Filter] {filter_name}: SKIPPED. (Would reduce results to 0)") # Uncomment for debug
        return current_query


# ---------------------------------------------------------
# 2. MATCH ENDPOINTS
# ---------------------------------------------------------

@router.post("/me/unmatch/{other_user_id}")
def unmatch_user(
        other_user_id: int,
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    match = db.query(Match).filter(
        ((Match.user1_id == current_user.user_id) & (Match.user2_id == other_user_id)) |
        ((Match.user2_id == current_user.user_id) & (Match.user1_id == other_user_id)),
        Match.match_status == 'active'
    ).first()

    if not match:
        raise HTTPException(status_code=404, detail="Active match not found.")

    match.match_status = "unmatched"
    db.commit()
    return {"message": "Unmatched successfully."}


@router.get("/me/matches", response_model=List[ProfileSummary])
def get_matches(
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db),
        limit: int = 10
):
    matches = db.query(Match).filter(
        ((Match.user1_id == current_user.user_id) | (Match.user2_id == current_user.user_id)),
        Match.match_status == 'active'
    ).order_by(Match.compatibility_score.desc()).limit(limit).all()

    match_user_ids = [m.user2_id if m.user1_id == current_user.user_id else m.user1_id for m in matches]
    if not match_user_ids:
        return []

    # Exclude disliked
    try:
        disliked_subq = db.query(Like.liked_user_id).filter(
            Like.liker_user_id == current_user.user_id,
            Like.status == 'disliked'
        ).subquery()

        profiles = db.query(Profile).filter(
            Profile.user_id.in_(match_user_ids),
            ~Profile.user_id.in_(disliked_subq),
            Profile.user_id.in_(active_user_ids_query(db))
        ).all()
    except Exception:
        profiles = db.query(Profile).filter(
            Profile.user_id.in_(match_user_ids),
            Profile.user_id.in_(active_user_ids_query(db))
        ).all()

    return [ProfileSummary.model_validate(p, from_attributes=True) for p in profiles]


# ---------------------------------------------------------
# 3. PREFERRED PROFILES (Adaptive Filtering)
# ---------------------------------------------------------

@router.post("/me/preferred-profiles", response_model=List[ProfileSummary])
def get_preferred_profiles(
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db),
        limit: int = 20,
        offset: int = 0
):
    user_profile = db.query(Profile).filter(Profile.user_id == current_user.user_id).first()
    prefs = db.query(Preference).filter(Preference.user_id == current_user.user_id).first()

    if not user_profile or not prefs:
        return []

    # 1. BASE QUERY (Strict Requirements)
    query = db.query(Profile).filter(
        Profile.user_id != current_user.user_id,
        Profile.is_verified == 1,
        Profile.is_hidden == 0,
        Profile.is_approved == 1
    )

    # 2. GENDER FILTER (Strict)
    if prefs.looking_for:
        target_genders = _looking_for_to_genders_local(prefs.looking_for, user_profile.gender)
        if target_genders:
            query = query.filter(func.lower(Profile.gender).in_(target_genders))

    # 3. NUMERIC FILTERS (Strict)
    today = datetime.date.today()
    if prefs.min_age:
        query = query.filter(Profile.date_of_birth <= datetime.date(today.year - prefs.min_age, today.month, today.day))
    if prefs.max_age:
        query = query.filter(
            Profile.date_of_birth >= datetime.date(today.year - prefs.max_age - 1, today.month, today.day))

    if prefs.min_height_cm: query = query.filter(Profile.height_cm >= prefs.min_height_cm)
    if prefs.max_height_cm: query = query.filter(Profile.height_cm <= prefs.max_height_cm)

    if prefs.min_salary_expectation: query = query.filter(Profile.annual_salary_npr >= prefs.min_salary_expectation)

    # -----------------------------------------------------
    # 4. ADAPTIVE TEXT FILTERS
    # -----------------------------------------------------

    query = _apply_filter_safely(query, Profile.marital_status, prefs.preferred_marital_status_text, "Marital Status")
    query = _apply_filter_safely(query, Profile.religion_text, prefs.preferred_religions_text, "Religion")
    query = _apply_filter_safely(query, Profile.caste_text, prefs.preferred_castes_text, "Caste")
    query = _apply_filter_safely(query, Profile.mother_tongue, prefs.preferred_mother_tongue, "Language")
    query = _apply_filter_safely(query, Profile.education_level_text, prefs.preferred_education_levels_text, "Edu Level")
    query = _apply_filter_safely(query, Profile.profession_text, prefs.preferred_professions_text, "Profession")

    if hasattr(Profile, 'education_field_text'):
        query = _apply_filter_safely(query, Profile.education_field_text, prefs.preferred_education_field_text, "Edu Field")

    query = _apply_filter_safely(query, Profile.smoking_habits, prefs.preferred_smoking_habits, "Smoking")
    query = _apply_filter_safely(query, Profile.drinking_habits, prefs.preferred_drinking_habits, "Drinking")
    query = _apply_filter_safely(query, Profile.dietary_preferences, prefs.preferred_dietary_habits, "Diet")
    query = _apply_filter_safely(query, Profile.manglik_status, prefs.preferred_manglik_status, "Manglik")

    # 6. LOCATION (Adaptive)
    if prefs.preferred_locations_text:
        temp_query = _apply_address_like_filter(query, Profile.city_text, prefs.preferred_locations_text)
        if temp_query.count() > 0:
            query = temp_query

    # 7. EXECUTE
    query = query.order_by(Profile.verified_at.desc())
    profiles = query.offset(offset).limit(limit).all()

    return profiles
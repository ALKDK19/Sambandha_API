import uuid
from typing import List, Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy import func, desc, or_, and_
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.database import get_db
from app.models.interaction import Like, ProfileVisit
from app.models.preference import Preference
from app.models.profile import Profile
from app.models.recommender import Recommendation
from app.models.security import BlockedUser
from app.models.shortlist import Shortlist
from app.models.user import User
from app.schemas.profile import ProfileCreate, ProfileUpdate, ProfileInDB, ProfileSummary, ProfileCompletionSuggestion
from app.schemas.user import UserInDB
from utilities.cloudinary import upload_image_to_cloudinary, delete_image_from_cloudinary, upload_media_to_cloudinary, \
    get_public_id_from_url
from utilities.recsys.embedding_utils import update_profile_embedding
from utilities.recsys.match_maker import MatchMaker
from utilities.recsys.recommender import Recommender
from utilities.security import get_current_user, get_optional_current_user, active_user_ids_query

router = APIRouter()


def _looking_for_to_genders(looking_for: str | None, fallback_gender: str | None = None) -> list[str]:
    """Map different possible `looking_for` values to profile.gender values.
    Accepts values like 'bride', 'bridegroom', 'male', 'female' or comma-separated combos.
    Returns a list of lowercase genders to filter on (e.g. ['female']). If 'Any' is specified returns []
    (meaning no gender filtering), and if empty and fallback_gender is provided, returns [fallback_gender].
    """
    if not looking_for:
        return [fallback_gender] if fallback_gender else []
    text = looking_for.lower()
    parts = [p.strip() for p in text.split(',') if p.strip()]
    genders: list[str] = []
    for p in parts:
        if p == 'any':
            # any => no specific gender filter
            return []
        if p in ('bride', 'bridegroom'):
            # map bride -> female, bridegroom -> male
            if p == 'bride' and 'female' not in genders:
                genders.append('female')
            if p == 'bridegroom' and 'male' not in genders:
                genders.append('male')
        elif p in ('male', 'female', 'other'):
            if p not in genders:
                genders.append(p)
        else:
            # fuzzy: if contains 'bride' assume female, 'groom' assume male
            if 'bride' in p and 'female' not in genders:
                genders.append('female')
            if 'groom' in p and 'male' not in genders:
                genders.append('male')
    if not genders and fallback_gender:
        return [fallback_gender]
    return genders


def calculate_profile_completion(profile: Any) -> tuple[int, list, list]:
    """
    Returns (completion_percentage, missing_fields, suggestions)
    """
    required_fields = [
        ("first_name", "Add your first name"),
        ("last_name", "Add your last name"),
        ("date_of_birth", "Add your date of birth"),
        ("gender", "Specify your gender"),
        ("height_cm", "Add your height"),
        ("marital_status", "Specify your marital status"),
        ("address", "Add your address"),
        ("city_text", "Add your city"),
        ("country", "Add your country"),
        ("primary_profile_image_url", "Upload a profile picture"),
        ("annual_salary_npr", "Add your annual salary"),
        ("video_introduction_url", "Upload a video introduction"),
        ("education_level_text", "Add your education level"),
        ("education_field_text", "Add your education field"),
        ("profession_text", "Add your profession"),
        ("bio", "Write a short bio"),
        ("religion_text", "Specify your religion"),
        ("caste_text", "Specify your caste"),
        ("mother_tongue", "Specify your mother tongue"),
        ("family_type", "Specify your family type"),
        ("dietary_preferences", "Specify your dietary preferences"),
        ("smoking_habits", "Specify your smoking habits"),
        ("drinking_habits", "Specify your drinking habits"),
        ("hobbies_interests", "Add your hobbies/interests"),
        ("rashi", "Add your rashi (zodiac sign)"),
        ("nakshatra", "Add your nakshatra"),
        ("gotra", "Add your gotra"),
        ("manglik_status", "Specify your manglik status"),
        ("birth_time", "Add your birth time"),
        ("birth_place", "Add your birth place"),
        ("kundali_image_url", "Upload your kundali image"),
    ]
    filled = 0
    missing = []
    suggestions = []
    for field, suggestion in required_fields:
        if getattr(profile, field, None):
            filled += 1
        else:
            missing.append(field)
            suggestions.append(suggestion)
    percent = int(round((filled / len(required_fields)) * 100))
    return percent, missing, suggestions


@router.post("/", response_model=ProfileInDB)
def create_profile(
        profile: ProfileCreate,
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    db_profile = db.query(Profile).filter(Profile.user_id == current_user.user_id).first()
    if db_profile:
        raise HTTPException(status_code=400, detail="Profile already exists")
    profile_dict = profile.model_dump()
    profile_dict["user_id"] = current_user.user_id
    # SQLAlchemy model construction using kwargs is valid at runtime; static type checkers may warn here
    new_profile = Profile(**profile_dict)  # type: ignore[arg-type]
    # Calculate and set profile completion percentage
    percent, _, _ = calculate_profile_completion(new_profile)
    new_profile.profile_completion_percentage = percent
    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)
    try:
        update_profile_embedding(db, new_profile)
    except Exception:
        pass
    return ProfileInDB.model_validate(new_profile, from_attributes=True)


@router.get("/me", response_model=ProfileInDB)
def read_current_profile(
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    db_profile = db.query(Profile).filter(Profile.user_id == current_user.user_id).first()  # type: ignore[call-arg]
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return ProfileInDB.model_validate(db_profile, from_attributes=True)


@router.put("/me", response_model=ProfileInDB)
def update_profile(
        profile: ProfileUpdate,
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    db_profile = db.query(Profile).filter(Profile.user_id == current_user.user_id).first()  # type: ignore[call-arg]
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    for key, value in profile.model_dump(exclude_unset=True).items():
        setattr(db_profile, key, value)
    # Recalculate profile completion percentage
    percent, _, _ = calculate_profile_completion(db_profile)
    db_profile.profile_completion_percentage = percent
    db.commit()
    db.refresh(db_profile)

    try:
        update_profile_embedding(db, db_profile)
    except Exception:
        pass
    try:
        mm = MatchMaker(db)
        mm.create_matches_from_recs(user_id=current_user.user_id, limit=50)
    except Exception:
        pass
    return ProfileInDB.model_validate(db_profile, from_attributes=True)


# --- User: Request profile verification ---
@router.post("/me/request-verification")
def upload_government_id(
        file: UploadFile = File(...),
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    db_profile = db.query(Profile).filter(Profile.user_id == current_user.user_id).first()  # type: ignore[call-arg]
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    if db_profile.is_verified:
        raise HTTPException(status_code=403, detail="You have already verified your identity")

    if db_profile.profile_completion_percentage < 80:
        raise HTTPException(status_code=400, detail="Profile must be at least 80% complete to request verification.")

    # check file exists
    if not file:
        raise HTTPException(status_code=400, detail="Government ID must be uploaded to request verification")

    # If an existing government_id_url exists, attempt to delete it from Cloudinary
    if db_profile.government_id_url:
        old_public_id = get_public_id_from_url(db_profile.government_id_url)
        if old_public_id:
            try:
                delete_image_from_cloudinary(old_public_id, resource_type='image')
            except Exception:
                pass

    # Define a unique public_id to allow overwriting
    public_id = f"user_{current_user.user_id}_govtid_{uuid.uuid4().hex}"

    # Upload to Cloudinary
    image_url = upload_image_to_cloudinary(
        file=file,
        folder="sambandha/government_ids",
        public_id=public_id
    )

    db_profile.government_id_url = image_url
    db_profile.verification_status = "requested"

    db.commit()
    db.refresh(db_profile)

    return JSONResponse(
        status_code=200,
        content={"message": "Government ID uploaded successfully. It ll be in review for now."},
    )


# --- NEW ENDPOINTS FOR EXPLORE SCREEN ---
# These must be placed BEFORE the "/{user_id}" endpoint.

@router.get("/popular", response_model=List[ProfileSummary])
def get_popular_profiles(
        limit: int = 10,
        db: Session = Depends(get_db),
        current_user: UserInDB | None = Depends(get_optional_current_user)
):
    """
    Returns a list of the most popular (most liked) user profiles.
    This is an unprotected endpoint for the Explore screen. If the request provides a valid
    user token, the user's own profile will be excluded from the results.
    """
    # Subquery to count likes for each user
    like_counts = db.query(
        Like.liked_user_id,
        func.count(Like.like_id).label('like_count')
    ).group_by(Like.liked_user_id).subquery()

    # Query profiles and join with like counts, ordering by popularity
    # Only include verified profiles
    query = db.query(Profile).join(
        like_counts, Profile.user_id == like_counts.c.liked_user_id
    ).filter(
        Profile.is_verified == 1,
        Profile.verification_status == 'verified'
    ).order_by(
        desc(like_counts.c.like_count)
    )

    # Ensure we only return active users' profiles
    query = query.filter(Profile.user_id.in_(active_user_ids_query(db)))

    if current_user:
        query = query.filter(Profile.user_id != current_user.user_id)
        # Exclude any profiles the current user has disliked
        try:
            disliked_subq = db.query(Like.liked_user_id).filter(
                Like.liker_user_id == current_user.user_id,
                Like.status == 'disliked'
            ).subquery()
            query = query.filter(~Profile.user_id.in_(disliked_subq))  # type: ignore[attr-defined]
        except Exception:
            pass

    popular_profiles = query.limit(limit).all()

    return [ProfileSummary.model_validate(p, from_attributes=True) for p in popular_profiles]


@router.get("/recent", response_model=List[ProfileSummary])
def get_recent_profiles(
        limit: int = 10,
        db: Session = Depends(get_db),
        current_user: UserInDB | None = Depends(get_optional_current_user)
):
    # Only include verified profiles in recents and order by newest
    query = db.query(Profile).filter(
        Profile.is_verified == 1,
        Profile.verification_status == 'verified'
    ).order_by(
        desc(Profile.profile_id)  # Assuming higher ID = newer profile
    )

    # Only include active users
    query = query.filter(Profile.user_id.in_(active_user_ids_query(db)))

    if current_user:
        query = query.filter(Profile.user_id != current_user.user_id)
        try:
            disliked_subq = db.query(Like.liked_user_id).filter(
                Like.liker_user_id == current_user.user_id,
                Like.status == 'disliked'
            ).subquery()
            query = query.filter(~Profile.user_id.in_(disliked_subq))  # type: ignore[attr-defined]
        except Exception:
            pass
    recent_profiles = query.limit(limit).all()

    return [ProfileSummary.model_validate(p, from_attributes=True) for p in recent_profiles]


# --- END OF NEW ENDPOINTS ---


@router.get("/", response_model=List[ProfileSummary])
def search_profiles(
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db),
        age_min: int = None,
        age_max: int = None,
        religion: str = None,
        caste: str = None,
        location: str = None,
        education: str = None,
        occupation: str = None,
        salary_min: int = None,
        salary_max: int = None,
        limit: int = 10,
        offset: int = 0
):
    query = db.query(Profile).filter(Profile.user_id != current_user.user_id, Profile.profile_visibility == 'public')
    if age_min or age_max:
        from datetime import date
        from dateutil.relativedelta import relativedelta
        today = date.today()
        if age_min:
            max_dob = today - relativedelta(years=age_min)
            query = query.filter(Profile.date_of_birth <= max_dob)
        if age_max:
            min_dob = today - relativedelta(years=age_max + 1) + relativedelta(days=1)
            query = query.filter(Profile.date_of_birth >= min_dob)
    if religion:
        query = query.filter(Profile.religion_text == religion)
    if caste:
        query = query.filter(Profile.caste_text == caste)
    if location:
        query = query.filter(or_(Profile.city_text == location, Profile.country == location))
    if education:
        query = query.filter(Profile.education_level_text == education)
    if occupation:
        query = query.filter(Profile.profession_text == occupation)
    if salary_min is not None:
        query = query.filter(Profile.annual_salary_npr >= salary_min)
    if salary_max is not None:
        query = query.filter(Profile.annual_salary_npr <= salary_max)
    blocked_by_me = db.query(BlockedUser.blocked_user_id).filter(
        BlockedUser.blocker_user_id == current_user.user_id).all()  # type: ignore[call-arg]
    # Users who have blocked the current user: select the blocker_user_id
    blocked_me = db.query(BlockedUser.blocker_user_id).filter(
        BlockedUser.blocked_user_id == current_user.user_id).all()  # type: ignore[call-arg]
    blocked_user_ids = set([bu[0] for bu in blocked_by_me] + [bu[0] for bu in blocked_me])
    if blocked_user_ids:
        query = query.filter(~Profile.user_id.in_(blocked_user_ids))  # type: ignore[attr-defined]
    # Ensure only profiles of active users are returned. Use a subquery to avoid loading ids into memory.
    query = query.filter(Profile.user_id.in_(active_user_ids_query(db)))

    # Exclude profiles that the current user has DISLIKED
    try:
        disliked_subq = db.query(Like.liked_user_id).filter(
            Like.liker_user_id == current_user.user_id,
            Like.status == 'disliked'
        ).subquery()
        query = query.filter(~Profile.user_id.in_(disliked_subq))  # type: ignore[attr-defined]
    except Exception:
        pass

    profiles = query.offset(offset).limit(limit).all()
    return [ProfileSummary.model_validate(p, from_attributes=True) for p in profiles]


# New endpoint: authenticated users can request all profiles filtered by opposite gender
@router.get("/all", response_model=List[ProfileSummary])
def get_all_profiles(
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db),
        limit: int = 100,
        offset: int = 0
):
    """
    Return profiles visible to a logged-in user. By default, this endpoint returns public, active profiles
    of the opposite gender to the current user (male -> female, female -> male). The current user
    and any blocked users (either direction) are excluded. Uses the user's `looking_for` preference
    when set to determine which genders to include.
    """
    # Try to get the current user's profile to determine their gender (UserInDB doesn't carry gender)
    current_profile = db.query(Profile).filter(
        Profile.user_id == current_user.user_id).first()  # type: ignore[call-arg]
    user_gender = getattr(current_profile, 'gender', None) if current_profile else None

    # Try to read preferences and compute target genders from `looking_for` first
    prefs = db.query(Preference).filter(Preference.user_id == current_user.user_id).first()
    target_genders = []
    if prefs and prefs.looking_for:
        target_genders = _looking_for_to_genders(prefs.looking_for)

    # If no explicit looking_for mapping, fall back to the opposite gender
    if not target_genders and user_gender:
        if user_gender.lower() == 'male':
            target_genders = ['female']
        elif user_gender.lower() == 'female':
            target_genders = ['male']

    print("===================================================")
    print(target_genders)
    print("===================================================")

    # Base query: exclude self, require public visibility
    query = db.query(Profile).filter(Profile.user_id != current_user.user_id, Profile.profile_visibility == 'public')

    # Ensure only active users
    query = query.filter(Profile.user_id.in_(active_user_ids_query(db)))

    # Apply gender filter if we could determine target genders
    if target_genders:
        query = query.filter(func.lower(Profile.gender).in_([g.lower() for g in target_genders]))

    # Exclude blocked users (either blocked by me or who blocked me)
    blocked_by_me = db.query(BlockedUser.blocked_user_id).filter(
        BlockedUser.blocker_user_id == current_user.user_id).all()  # type: ignore[call-arg]
    # Users who have blocked the current user: select the blocker_user_id
    blocked_me = db.query(BlockedUser.blocker_user_id).filter(
        BlockedUser.blocked_user_id == current_user.user_id).all()  # type: ignore[call-arg]
    blocked_user_ids = set([bu[0] for bu in blocked_by_me] + [bu[0] for bu in blocked_me])
    if blocked_user_ids:
        query = query.filter(~Profile.user_id.in_(blocked_user_ids))  # type: ignore[attr-defined]

    # Exclude profiles that the current user has DISLIKED
    # (i.e., there exists a Like row where liker_user_id == current_user.user_id and status == 'disliked')
    try:
        disliked_subq = db.query(Like.liked_user_id).filter(
            Like.liker_user_id == current_user.user_id,
            Like.status == 'disliked'
        ).subquery()
        query = query.filter(~Profile.user_id.in_(disliked_subq))  # type: ignore[attr-defined]
    except Exception:
        # If anything goes wrong building the subquery, proceed without this filter (best-effort)
        pass

    # 1. Fetch profiles first
    profiles = query.offset(offset).limit(limit).all()
    profile_user_ids = [p.user_id for p in profiles]

    profile_user_names = [p.first_name for p in profiles]
    print("===================================================")
    print(query)
    print(profile_user_names)
    print("===================================================")

    # 2. In a single query, find which of these profiles the current user has liked
    # Fetch like rows (liked_user_id, like_id, like_type) so we have both id and type
    like_rows = db.query(Like.liked_user_id, Like.like_id, Like.like_type).filter(
        Like.liker_user_id == current_user.user_id,
        Like.liked_user_id.in_(profile_user_ids),
        Like.status == 'active'
    ).all()
    # Build a mapping from liked_user_id -> {"like_id": ..., "like_type": ...}
    liked_map = {}
    for liked_user_id, like_id, like_type in like_rows:
        # If multiple rows exist for the same target, prefer the latest one encountered
        liked_map[liked_user_id] = {"like_id": like_id, "like_type": like_type}

    # 2b. Fetch shortlist rows in a single query so we can set is_shortlisted efficiently
    try:
        shortlist_rows = db.query(Shortlist.shortlisted_user_id).filter(
            Shortlist.user_id == current_user.user_id,
            Shortlist.shortlisted_user_id.in_(profile_user_ids)
        ).all()
        shortlisted_set = set([sr[0] for sr in shortlist_rows])
    except Exception:
        shortlisted_set = set()

    print("================================================")
    print(liked_map)
    print("================================================")

    # 3. Create the response models, setting the 'is_liked' flag
    response_profiles = []
    for p in profiles:
        profile_summary = ProfileSummary.model_validate(p, from_attributes=True)
        like_info = liked_map.get(p.user_id)
        profile_summary.is_liked = bool(like_info)
        # Attach like_type if available so the frontend can use it directly
        if like_info and "like_type" in like_info:
            try:
                profile_summary.like_type = like_info["like_type"]
            except Exception:
                # If the schema/model doesn't accept assignment, ignore silently
                pass
        # Set shortlist flag
        try:
            profile_summary.is_shortlisted = p.user_id in shortlisted_set
        except Exception:
            pass
        response_profiles.append(profile_summary)

    return response_profiles


@router.get("/public/browse", response_model=List[ProfileSummary])
def browse_public_profiles(
        db: Session = Depends(get_db),
        limit: int = 10,
        offset: int = 0,
        current_user: UserInDB | None = Depends(get_optional_current_user)
):
    """
    An unprotected endpoint for guest users to browse a generic
    list of public active profiles.
    If a valid user token is provided, exclude the current user's profile from results.
    """
    # Find active user IDs
    # Use helper to build a subquery so we don't load ids into memory

    query = db.query(Profile).filter(
        Profile.user_id.in_(active_user_ids_query(db)),  # type: ignore[attr-defined]
        Profile.profile_visibility == 'public',  # type: ignore[comparison-overlap]
        Profile.primary_profile_image_url is not None  # Ensure they have a photo # type: ignore[comparison-overlap]
    )

    if current_user:
        query = query.filter(Profile.user_id != current_user.user_id)
        try:
            disliked_subq = db.query(Like.liked_user_id).filter(
                Like.liker_user_id == current_user.user_id,
                Like.status == 'disliked'
            ).subquery()
            query = query.filter(~Profile.user_id.in_(disliked_subq))  # type: ignore[attr-defined]
        except Exception:
            pass

    profiles = query.order_by(
        func.random()  # Order randomly for variety. Use .order_by(Profile.created_at.desc()) for newest profiles
    ).offset(offset).limit(limit).all()

    return [ProfileSummary.model_validate(p, from_attributes=True) for p in profiles]


# Reinsert the dynamic profile read endpoint after static routes to avoid routing conflicts
@router.get("/{user_id}", response_model=ProfileSummary)
def read_profile(
        user_id: int,
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    # Check if a user is blocked
    blocked = db.query(BlockedUser).filter(
        or_(and_(BlockedUser.blocker_user_id == current_user.user_id, BlockedUser.blocked_user_id == user_id),
            and_(BlockedUser.blocker_user_id == user_id, BlockedUser.blocked_user_id == current_user.user_id))).first()

    # Check if the target user is deactivated
    target_user = db.query(User).filter(User.user_id == user_id).first()  # type: ignore[call-arg]
    if not target_user or not target_user.is_active:
        raise HTTPException(status_code=404, detail="Profile not found or user is deactivated")

    if blocked:
        raise HTTPException(status_code=403, detail="You are blocked from viewing this profile")

    # If the current user has previously disliked this target, do not expose the profile
    try:
        disliked = db.query(Like).filter(
            Like.liker_user_id == current_user.user_id,
            Like.liked_user_id == user_id,
            Like.status == 'disliked'
        ).first()
        if disliked:
            raise HTTPException(status_code=404, detail="Profile not found")
    except Exception:
        # On DB errors, fall through and continue (best-effort)
        pass

    db_profile = db.query(Profile).filter(Profile.user_id == user_id).first()  # type: ignore[call-arg]
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Record profile visit
    visit = ProfileVisit()
    visit.visitor_user_id = current_user.user_id
    visit.visited_profile_user_id = user_id
    db.add(visit)
    db.commit()

    # Return only ProfileSummary (which does not include government_id_url)
    #  Additionally, set is_liked and like_type if the current user has an active like record
    profile_summary = ProfileSummary.model_validate(db_profile, from_attributes=True)
    try:
        like_row = db.query(Like.like_id, Like.like_type).filter(
            Like.liker_user_id == current_user.user_id,
            Like.liked_user_id == user_id,
            Like.status == 'active'
        ).first()
        if like_row:
            # like_row can be a tuple (like_id, like_type) depending on the DB driver
            try:
                # If it's a Row or tuple-like
                like_id_val = like_row[0]
                like_type_val = like_row[1]
            except Exception:
                # Fallback if it's an object with attributes
                like_id_val = getattr(like_row, 'like_id', None)
                like_type_val = getattr(like_row, 'like_type', None)
            profile_summary.is_liked = True
            try:
                profile_summary.like_type = like_type_val
            except Exception:
                # If the schema/model doesn't accept assignment, ignore silently
                pass
        else:
            profile_summary.is_liked = False
    except Exception:
        # Best-effort: if a DB query fails, return the profile without like info
        pass

    # Set shortlist flag for single profile read
    try:
        shortlist_entry = db.query(Shortlist).filter(
            Shortlist.user_id == current_user.user_id,
            Shortlist.shortlisted_user_id == user_id
        ).first()
        profile_summary.is_shortlisted = bool(shortlist_entry)
    except Exception:
        # Best-effort: ignore DB errors and leave is_shortlisted as-is
        pass

    return profile_summary


@router.post("/me/upload-profile-image")
def upload_profile_image(
        file: UploadFile = File(...),
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    db_profile = db.query(Profile).filter(Profile.user_id == current_user.user_id).first()  # type: ignore[call-arg]
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # If an existing profile image exists, try to delete it from Cloudinary
    if db_profile.primary_profile_image_url:
        old_public_id = get_public_id_from_url(db_profile.primary_profile_image_url)
        if old_public_id:
            try:
                delete_image_from_cloudinary(old_public_id, resource_type='image')
            except Exception:
                pass

    # Define a unique public_id for the user's profile picture. This ensures they only have one.
    public_id = f"user_{current_user.user_id}_profile"

    image_url = upload_image_to_cloudinary(
        file=file,
        folder="sambandha/profile_images",
        public_id=public_id
    )

    db_profile.primary_profile_image_url = image_url
    db.commit()
    db.refresh(db_profile)

    return JSONResponse(
        status_code=200,
        content={"message": "Profile image uploaded successfully",
                 "profile_image_url": db_profile.primary_profile_image_url})


@router.post("/me/upload-additional-images")
def upload_additional_images(
        files: List[UploadFile] = File(...),
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    db_profile = db.query(Profile).filter(Profile.user_id == current_user.user_id).first()  # type: ignore[call-arg]
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Make a defensive (shallow) copy of existing additional images so we don't mutate
    # the mapped attribute in-place and confuse the ORM change detection.
    image_urls = list(db_profile.additional_multiple_images) if db_profile.additional_multiple_images else []

    print("Uploading {} additional images for user {}".format(len(files), current_user.user_id))

    for file in files:
        # For additional images, we want a random public_id for each one
        public_id = f"user_{current_user.user_id}_additional_{uuid.uuid4().hex}"

        url = upload_image_to_cloudinary(
            file=file,
            folder="sambandha/additional_images",
            public_id=public_id
        )

        # Only append if the URL is valid and not already present in our list
        if url and url not in image_urls:
            image_urls.append(url)
            print(f"Uploaded {url} for user {current_user.user_id}")

    # Ensure deterministic deduplication (preserve order)
    deduped = []
    for u in image_urls:
        if u not in deduped:
            deduped.append(u)

    # Assign a fresh list instance to the mapped attribute so SQLAlchemy reliably detects the change
    db_profile.additional_multiple_images = deduped
    # Mark the JSON attribute as modified in case the dialect/mapper needs an explicit signal
    try:
        flag_modified(db_profile, 'additional_multiple_images')
    except Exception:
        pass
    # Ensure the instance is attached to the session (should already be) then commit
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)

    # Return the value that was actually persisted (so frontend and DB are consistent)
    return JSONResponse(
        status_code=200,
        content={"message": "Additional images uploaded successfully",
                 "additional_images": db_profile.additional_multiple_images}
    )


@router.delete("/me/delete-additional-image")
def delete_additional_image(
        image_url: str,  # We receive the full URL from the client
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    db_profile = db.query(Profile).filter(Profile.user_id == current_user.user_id).first()  # type: ignore[call-arg]
    if not db_profile or not db_profile.additional_multiple_images:
        raise HTTPException(status_code=404, detail="No additional images found")

    # Work with a copy of the stored URLs to avoid in-place mutations that SQLAlchemy
    # might not detect for JSON columns. Also support matching by public_id when the
    # provided URL differs in minor encoding or versioning.
    stored_urls = list(db_profile.additional_multiple_images or [])

    # Try the exact match first, otherwise try matching by Cloudinary public_id
    target_url = None
    if image_url in stored_urls:
        target_url = image_url
    else:
        try:
            requested_pid = get_public_id_from_url(image_url)
            if requested_pid:
                for u in stored_urls:
                    pid = get_public_id_from_url(u)
                    if pid and pid == requested_pid:
                        target_url = u
                        break
        except Exception as e:
            print(f"Error matching by public_id: {e}")

    if not target_url:
        raise HTTPException(status_code=404, detail="Image URL not found in profile")

    # Attempt to delete from Cloudinary (best-effort). Ignore deletion errors.
    try:
        public_id = get_public_id_from_url(target_url)
        if public_id:
            delete_image_from_cloudinary(public_id, resource_type='image')
    except Exception as e:
        print(f"Could not delete image from Cloudinary for {target_url}: {e}")

    # Produce a new list instance so SQLAlchemy detects the change and persists it.
    new_urls = [u for u in stored_urls if u != target_url]

    print("=================================================")
    print(f"Deleted {target_url} for user {current_user.user_id}")
    print(new_urls)
    print("=================================================")

    db_profile.additional_multiple_images = new_urls
    try:
        flag_modified(db_profile, 'additional_multiple_images')
    except Exception:
        pass
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return JSONResponse({"message": "Image deleted", "additional_images": new_urls})


@router.get("/me/completion-suggestions", response_model=ProfileCompletionSuggestion)
def get_profile_completion_suggestions(
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    db_profile = db.query(Profile).filter(Profile.user_id == current_user.user_id).first()  # type: ignore[call-arg]
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    percent, missing, suggestions = calculate_profile_completion(db_profile)
    return ProfileCompletionSuggestion(
        completion_percentage=percent,
        missing_fields=missing,
        suggestions=suggestions
    )


@router.post("/me/recommendations", response_model=List[ProfileSummary])
def get_recommendations(
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db),
        limit: int = 10
):
    recommender = Recommender(db)
    recommender.recommend(current_user.user_id, top_n=limit)
    recs = db.query(Recommendation).filter(Recommendation.user_id == current_user.user_id,
                                           Recommendation.status == 'active').order_by(
        Recommendation.recommendation_score.desc()).limit(limit).all()
    user_ids = [r.recommended_user_id for r in recs]

    profiles = db.query(Profile).filter(
        Profile.user_id.in_(user_ids),
    ).all()

    return [ProfileSummary.model_validate(p, from_attributes=True) for p in profiles]


@router.post("/me/upload-kundali-image")
def upload_kundali_image(
        file: UploadFile = File(...),
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Upload/replace user's kundali (horoscope) image."""
    db_profile = db.query(Profile).filter(Profile.user_id == current_user.user_id).first()  # type: ignore[call-arg]
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Delete previous kundali image in cloudinary if present
    if db_profile.kundali_image_url:
        old_public_id = get_public_id_from_url(db_profile.kundali_image_url)
        if old_public_id:
            try:
                delete_image_from_cloudinary(old_public_id, resource_type='image')
            except Exception:
                pass

    public_id = f"user_{current_user.user_id}_kundali"

    image_url = upload_image_to_cloudinary(
        file=file,
        folder="sambandha/kundali_images",
        public_id=public_id
    )

    db_profile.kundali_image_url = image_url
    db.commit()
    db.refresh(db_profile)

    return JSONResponse(status_code=200, content={"message": "Kundali image uploaded successfully",
                                                  "kundali_image_url": image_url})


@router.post("/me/upload-video-intro")
def upload_video_intro(
        file: UploadFile = File(...),
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Upload or replace the user's video introduction. Stored as a video resource in Cloudinary."""
    db_profile = db.query(Profile).filter(Profile.user_id == current_user.user_id).first()  # type: ignore[call-arg]
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Delete previous video intro in cloudinary if present
    if db_profile.video_intro_url:
        old_public_id = get_public_id_from_url(db_profile.video_intro_url)
        if old_public_id:
            try:
                delete_image_from_cloudinary(old_public_id, resource_type='video')
            except Exception:
                pass

    public_id = f"user_{current_user.user_id}_video_intro"

    # Use upload_media_to_cloudinary with resource_type='video'
    video_url = upload_media_to_cloudinary(
        file=file,
        folder="sambandha/video_intros",
        public_id=public_id,
        resource_type='video'
    )

    db_profile.video_intro_url = video_url
    db.commit()
    db.refresh(db_profile)

    return JSONResponse(status_code=200, content={"message": "Video intro uploaded successfully",
                                                  "video_intro_url": video_url})

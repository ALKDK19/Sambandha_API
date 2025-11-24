from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.interaction import Like
from app.models.profile import Profile  # Import Profile
from app.models.shortlist import Shortlist
from app.schemas.profile import ProfileSummary  # Import ProfileSummary
from app.schemas.shortlist import ShortlistCreate, ShortlistInDB
from app.schemas.user import UserInDB
from utilities.logging_config import logger
from utilities.security import get_current_user, active_user_ids_query

router = APIRouter()


@router.post("/", response_model=ShortlistInDB)
def add_to_shortlist(
        shortlist: ShortlistCreate,
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    if shortlist.shortlisted_user_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="Cannot shortlist yourself")
    # Check if already shortlisted
    existing = db.query(Shortlist).filter(
        Shortlist.user_id == current_user.user_id,
        Shortlist.shortlisted_user_id == shortlist.shortlisted_user_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already shortlisted")
    # Instantiate then set attributes to avoid type-checker warnings about unexpected constructor args
    new_shortlist = Shortlist()
    new_shortlist.user_id = current_user.user_id
    new_shortlist.shortlisted_user_id = shortlist.shortlisted_user_id
    db.add(new_shortlist)
    db.commit()
    db.refresh(new_shortlist)
    return new_shortlist


@router.delete("/{shortlisted_user_id}")
def remove_from_shortlist(
        shortlisted_user_id: int,
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    entry = db.query(Shortlist).filter(
        Shortlist.user_id == current_user.user_id,
        Shortlist.shortlisted_user_id == shortlisted_user_id
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Not in shortlist")
    db.delete(entry)
    db.commit()
    return {"message": "Removed from shortlist"}


@router.get("/", response_model=List[ProfileSummary])  # FIX: Changed response model
def get_my_shortlist(
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    # FIX: Query profiles of users that the current user has shortlisted.
    shortlisted_user_ids_query = db.query(Shortlist.shortlisted_user_id).filter(
        Shortlist.user_id == current_user.user_id
    )

    # Also exclude any users the current user has explicitly disliked
    try:
        disliked_subq = db.query(Like.liked_user_id).filter(
            Like.liker_user_id == current_user.user_id,
            Like.status == 'disliked'
        ).subquery()
        profiles = db.query(Profile).filter(
            Profile.user_id.in_(shortlisted_user_ids_query),
            ~Profile.user_id.in_(disliked_subq),
            Profile.user_id.in_(active_user_ids_query(db))
        ).all()
    except Exception:
        profiles = db.query(Profile).filter(
            Profile.user_id.in_(shortlisted_user_ids_query),
            Profile.user_id.in_(active_user_ids_query(db))
        ).all()

    # Exclude current user's own profile just in case
    profiles = [p for p in profiles if p.user_id != current_user.user_id]

    return profiles

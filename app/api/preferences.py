from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.preference import Preference
from app.schemas.preference import PreferenceCreate, PreferenceUpdate, PreferenceInDB
from app.schemas.user import UserInDB
from utilities.recsys.match_maker import MatchMaker
from utilities.security import get_current_user

router = APIRouter()


def _normalize_looking_for(raw: str | None) -> str | None:
    """Normalize a comma-separated looking_for string into canonical capitalized tokens.
    Example: 'male,female' -> 'Male, Female', 'bride'->'Bride'
    Unknown tokens get Title-cased.
    """
    if not raw:
        return None
    parts = [p.strip() for p in raw.split(',') if p.strip()]
    canon = []
    for p in parts:
        low = p.lower()
        if low == 'male':
            canon.append('Male')
        elif low == 'female':
            canon.append('Female')
        elif low == 'other':
            canon.append('Other')
        elif low == 'any':
            canon.append('Any')
        elif low == 'bride':
            canon.append('Bride')
        elif low == 'bridegroom' or low == 'groom':
            canon.append('Bridegroom')
        else:
            canon.append(p.strip().title())
    # Remove duplicates while preserving order
    seen = set()
    out = []
    for c in canon:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return ','.join(out)


@router.post("/", response_model=PreferenceInDB)
def create_preference(
        preference: PreferenceCreate,
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    # Check if a preference already exists
    db_pref = db.query(Preference).filter(Preference.user_id == current_user.user_id).first()
    if db_pref:
        raise HTTPException(status_code=400, detail="Preference already exists")

    # Normalize looking_for before creating
    pref_dict = preference.model_dump()
    if 'looking_for' in pref_dict and pref_dict['looking_for']:
        pref_dict['looking_for'] = _normalize_looking_for(pref_dict['looking_for'])

    # Create preference
    new_pref = Preference(**pref_dict, user_id=current_user.user_id)
    db.add(new_pref)
    db.commit()
    db.refresh(new_pref)

    return new_pref


@router.get("/me", response_model=PreferenceInDB)
def read_current_preference(
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    db_pref = db.query(Preference).filter(Preference.user_id == current_user.user_id).first()
    if not db_pref:
        raise HTTPException(status_code=404, detail="Preference not found")
    return db_pref


@router.put("/me", response_model=PreferenceInDB)
def update_preference(
        preference: PreferenceUpdate,
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    db_pref = db.query(Preference).filter(Preference.user_id == current_user.user_id).first()
    if not db_pref:
        raise HTTPException(status_code=404, detail="Preference not found")

    # Normalize looking_for if provided
    pref_updates = preference.model_dump(exclude_unset=True)
    if 'looking_for' in pref_updates and pref_updates['looking_for']:
        pref_updates['looking_for'] = _normalize_looking_for(pref_updates['looking_for'])

    for key, value in pref_updates.items():
        setattr(db_pref, key, value)

    db.commit()
    db.refresh(db_pref)

    # Re-run matchmaking after a preference update so matches reflect the latest preferences
    try:
        mm = MatchMaker(db)
        mm.create_matches_from_recs(user_id=current_user.user_id, limit=50)
    except Exception:
        # Best-effort: don't fail the update if matchmaking fails
        pass

    return db_pref

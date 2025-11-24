from datetime import timedelta, datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_, and_, func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.admin import Admin
from app.models.content import StaticContent, Announcement
from app.models.engagement import Notification
from app.models.interaction import Match, Like
from app.models.profile import Profile
from app.models.recommender import Recommendation
from app.models.security import BlockedUser, Report
from app.models.user import User
from app.schemas.admin import AdminCreate, AdminInDB, AdminToken, AdminUpdate
from app.schemas.base import MessageResponse
from app.schemas.content import (
    StaticContentCreate, StaticContentUpdate, StaticContentInDB,
    AnnouncementCreate, AnnouncementUpdate, AnnouncementInDB
)
from app.schemas.engagement import NotificationCreate, NotificationInDB
from app.schemas.interaction import MatchInDB
from app.schemas.profile import ProfileInDB
from app.schemas.recommender import RecommendationInDB
from app.schemas.security import BlockedUserInDB
from app.schemas.user import UserInDB
from utilities.cloudinary import get_public_id_from_url, delete_image_from_cloudinary
from utilities.notification import send_profile_verification_status_notification
from utilities.security import (
    get_admin_password_hash, verify_admin_password,
    create_admin_access_token, get_current_active_admin,
    get_current_superuser
)

router = APIRouter()


# --- ADMIN AUTHENTICATION & MANAGEMENT ---

@router.post("/register", response_model=AdminInDB)
async def register_admin(
        admin: AdminCreate,
        db: Session = Depends(get_db),
        current_admin: Admin = Depends(get_current_superuser)
):
    db_admin = db.query(Admin).filter(
        or_(Admin.username == admin.username, Admin.email == admin.email)
    ).first()
    if db_admin:
        raise HTTPException(status_code=400, detail="Admin with this username or email already exists")

    hashed_password = get_admin_password_hash(admin.password)
    new_admin = Admin()
    new_admin.username = admin.username
    new_admin.email = admin.email
    new_admin.full_name = admin.full_name
    new_admin.password_hash = hashed_password
    new_admin.is_active = True
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    return new_admin


@router.post("/login", response_model=AdminToken)
def login_admin(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db)
):
    admin = db.query(Admin).filter(Admin.username == form_data.username).first()
    if not admin or not verify_admin_password(form_data.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_admin_access_token(
        data={"admin_id": admin.admin_id}, expires_delta=access_token_expires
    )
    admin.last_login = datetime.now(timezone.utc)
    db.commit()
    return AdminToken(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=AdminInDB)
def read_current_admin(current_admin: Admin = Depends(get_current_active_admin)):
    return current_admin


@router.put("/me", response_model=AdminInDB)
def update_admin(
        admin_update: AdminUpdate,
        current_admin: Admin = Depends(get_current_active_admin),
        db: Session = Depends(get_db)
):
    if admin_update.password:
        current_admin.password_hash = get_admin_password_hash(admin_update.password)
    if admin_update.email:
        current_admin.email = admin_update.email
    if admin_update.username:
        current_admin.username = admin_update.username
    if admin_update.full_name:
        current_admin.full_name = admin_update.full_name
    db.commit()
    db.refresh(current_admin)
    return current_admin


# --- ADMIN USER ACCOUNT MANAGEMENT ---

@router.get("/users", response_model=List[UserInDB])
def get_users(
        status: Optional[str] = None,
        db: Session = Depends(get_db),
        current_admin: Admin = Depends(get_current_active_admin)
):
    query = db.query(User)
    if status is not None:
        if status == "active":
            query = query.filter(User.is_active == True)
        elif status == "inactive":
            query = query.filter(User.is_active == False)
    return query.all()


@router.post("/users/{user_id}/deactivate", response_model=MessageResponse)
def admin_deactivate_user(
        user_id: int,
        db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    user.deactivated_by = "admin"
    db.commit()
    return MessageResponse(message=f"User {user_id} deactivated")


@router.post("/users/{user_id}/reactivate", response_model=MessageResponse)
def admin_reactivate_user(
        user_id: int,
        db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.deactivated_by == "user":
        raise HTTPException(status_code=403, detail="Cannot reactivate a user who self-deactivated.")
    user.is_active = True
    user.deactivated_by = None
    db.commit()
    return MessageResponse(message=f"User {user_id} reactivated")


# --- ADMIN PROFILE MANAGEMENT ---

@router.get("/profiles/verification-requests", response_model=List[ProfileInDB])
def admin_list_verification_requests(
        db: Session = Depends(get_db),
        skip: int = 0,
        limit: int = 100
):
    profiles = db.query(Profile).filter(Profile.verification_status == "requested").offset(skip).limit(limit).all()
    return profiles


@router.patch("/profiles/{user_id}/verify", response_model=MessageResponse)
def verify_profile(
        user_id: int,
        db: Session = Depends(get_db),
        current_admin: Admin = Depends(get_current_active_admin)
):
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    if not profile.government_id_url:
        raise HTTPException(status_code=400, detail="Cannot verify profile without government ID uploaded")
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user or not user.phone_number or not user.is_phone_verified:
        raise HTTPException(status_code=400, detail="Cannot verify profile without a valid and verified phone number")

    profile.is_verified = 1
    profile.verified_at = datetime.now(timezone.utc)
    profile.verified_by_admin_id = current_admin.admin_id
    profile.verification_status = "verified"
    db.commit()
    send_profile_verification_status_notification(
        db, user_id, "verified", "Your profile has been verified successfully. You can now enjoy all features.")
    return MessageResponse(message="Profile verified successfully")


@router.patch("/profiles/{user_id}/cancel-verification", response_model=MessageResponse)
def cancel_profile_verification(
        user_id: int,
        db: Session = Depends(get_db)
):
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    if profile.verification_status != "requested":
        raise HTTPException(status_code=400, detail="No pending verification request to cancel.")

    profile.verification_status = "cancelled"
    db.commit()
    send_profile_verification_status_notification(
        db, user_id, "cancelled",
        "Your profile verification was not approved. Please update with valid details and request again.")
    return MessageResponse(message="Profile verification request has been cancelled.")


# --- ANALYTICS ---
@router.get("/analytics/summary")
def get_analytics_summary(db: Session = Depends(get_db), current_admin: Admin = Depends(get_current_active_admin)):
    users_count = db.query(User).count()
    profiles_count = db.query(Profile).count()
    matches_count = db.query(Match).filter(Match.match_status == 'active').count()
    likes_count = db.query(Like).filter(Like.status == 'active').count()
    return {"users": users_count, "profiles": profiles_count, "matches": matches_count, "likes": likes_count}


@router.get("/analytics/detailed")
def get_analytics_detailed(db: Session = Depends(get_db)):
    today = datetime.utcnow().date()
    daily_users = []
    for i in range(7):
        day = today - timedelta(days=i)
        count = db.query(User).filter(func.date(User.created_at) == day).count()
        daily_users.append({"date": str(day), "count": count})
    weekly_matches = []
    for i in range(4):
        week_start = today - timedelta(days=i * 7)
        week_end = week_start + timedelta(days=6)
        count = db.query(Match).filter(
            and_(func.date(Match.created_at) >= week_start, func.date(Match.created_at) <= week_end)).count()
        weekly_matches.append({"week_start": str(week_start), "count": count})
    gender_breakdown = db.query(Profile.gender, func.count(Profile.profile_id)).group_by(Profile.gender).all()
    gender_stats = [{"gender": g, "count": c} for g, c in gender_breakdown]
    country_breakdown = db.query(Profile.country, func.count(Profile.profile_id)).group_by(Profile.country).all()
    country_stats = [{"country": c, "count": n} for c, n in country_breakdown]
    return {
        "daily_users": daily_users,
        "weekly_matches": weekly_matches,
        "gender_breakdown": gender_stats,
        "country_breakdown": country_stats
    }


# --- USERS ---
@router.get("/users/active", response_model=List[UserInDB])
def get_active_users(db: Session = Depends(get_db)):
    return db.query(User).filter(User.is_active == True).all()


@router.get("/users/deactivated", response_model=List[UserInDB])
def get_deactivated_users(db: Session = Depends(get_db)):
    return db.query(User).filter(User.is_active == False).all()


# --- REPORTS ---
@router.get("/reports")
def get_reports(status: Optional[str] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(Report)
    if status:
        query = query.filter(Report.status == status)
    reports = query.offset(skip).limit(limit).all()
    return reports


@router.delete("/reports/{report_id}")
def delete_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.report_id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    db.delete(report)
    db.commit()
    return MessageResponse(message=f"Report {report_id} deleted")


# --- PROFILES ---
@router.get("/profiles", response_model=List[ProfileInDB])
def get_profiles(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Profile).offset(skip).limit(limit).all()


@router.get("/profiles/{user_id}", response_model=ProfileInDB)
def get_profile(user_id: int, db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.patch("/profiles/{user_id}/approve", response_model=MessageResponse)
def approve_profile(user_id: int, db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    profile.is_approved = 1
    db.commit()
    return MessageResponse(message="Profile approved")


@router.patch("/profiles/{user_id}/hide", response_model=MessageResponse)
def hide_profile(user_id: int, db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    profile.is_hidden = 1
    db.commit()
    return MessageResponse(message="Profile hidden")


@router.patch("/profiles/{user_id}/remove-photo", response_model=MessageResponse)
def remove_profile_photo(user_id: int, db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    profile.photo_url = None
    db.commit()
    return MessageResponse(message="Profile photo removed")


# --- STATIC CONTENT ---
@router.get("/static-content", response_model=List[StaticContentInDB])
def get_static_content(db: Session = Depends(get_db)):
    contents = db.query(StaticContent).all()
    return [StaticContentInDB.model_validate(c) for c in contents]


@router.get("/static-content/{key}", response_model=StaticContentInDB)
def get_static_content_by_key(key: str, db: Session = Depends(get_db)):
    content = db.query(StaticContent).filter(StaticContent.key == key).first()
    if not content:
        raise HTTPException(status_code=404, detail="Static content not found")
    return StaticContentInDB.model_validate(content)


@router.post("/static-content", response_model=StaticContentInDB)
def create_static_content(static_content: StaticContentCreate, db: Session = Depends(get_db)):
    new_content = StaticContent(**static_content.model_dump())
    db.add(new_content)
    db.commit()
    db.refresh(new_content)
    return StaticContentInDB.model_validate(new_content)


@router.put("/static-content/{key}", response_model=StaticContentInDB)
def update_static_content(key: str, static_content: StaticContentUpdate, db: Session = Depends(get_db)):
    content = db.query(StaticContent).filter(StaticContent.key == key).first()
    if not content:
        raise HTTPException(status_code=404, detail="Static content not found")
    update_data = static_content.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(content, k, v)
    db.commit()
    db.refresh(content)
    return StaticContentInDB.model_validate(content)


@router.delete("/static-content/{key}", response_model=MessageResponse)
def delete_static_content(key: str, db: Session = Depends(get_db)):
    content = db.query(StaticContent).filter(StaticContent.key == key).first()
    if not content:
        raise HTTPException(status_code=404, detail="Static content not found")
    db.delete(content)
    db.commit()
    return MessageResponse(message=f"Static content {key} deleted")


# --- ANNOUNCEMENTS ---
@router.get("/announcements", response_model=List[AnnouncementInDB])
def get_announcements(db: Session = Depends(get_db)):
    anns = db.query(Announcement).order_by(Announcement.created_at.desc()).all()
    return [AnnouncementInDB.model_validate(a) for a in anns]


@router.post("/announcements", response_model=AnnouncementInDB)
def create_announcement(announcement: AnnouncementCreate, db: Session = Depends(get_db)):
    new_announcement = Announcement(**announcement.model_dump())
    db.add(new_announcement)
    db.commit()
    db.refresh(new_announcement)
    return AnnouncementInDB.model_validate(new_announcement)


@router.put("/announcements/{id}", response_model=AnnouncementInDB)
def update_announcement(id: int, announcement: AnnouncementUpdate, db: Session = Depends(get_db)):
    ann = db.query(Announcement).filter(Announcement.id == id).first()
    if not ann:
        raise HTTPException(status_code=404, detail="Announcement not found")
    update_data = announcement.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(ann, k, v)
    db.commit()
    db.refresh(ann)
    return AnnouncementInDB.model_validate(ann)


@router.delete("/announcements/{id}", response_model=MessageResponse)
def delete_announcement(id: int, db: Session = Depends(get_db)):
    ann = db.query(Announcement).filter(Announcement.id == id).first()
    if not ann:
        raise HTTPException(status_code=404, detail="Announcement not found")
    db.delete(ann)
    db.commit()
    return MessageResponse(message=f"Announcement {id} deleted")


@router.delete("/profiles/{user_id}", response_model=MessageResponse)
def admin_delete_profile(
        user_id: int,
        db: Session = Depends(get_db)
):
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Here you would add logic to delete images from Cloudinary
    urls_to_delete = {
        'image': [],
        'video': []
    }
    if profile.primary_profile_image_url:
        urls_to_delete['image'].append(profile.primary_profile_image_url)
    if profile.government_id_url:
        urls_to_delete['image'].append(profile.government_id_url)
    if profile.kundali_image_url:
        urls_to_delete['image'].append(profile.kundali_image_url)
    if profile.additional_multiple_images:
        urls_to_delete['image'].extend(profile.additional_multiple_images)
    if profile.video_intro_url:
        urls_to_delete['video'].append(profile.video_intro_url)

    for resource_type, urls in urls_to_delete.items():
        for url in urls:
            public_id = get_public_id_from_url(url)
            if public_id:
                try:
                    delete_image_from_cloudinary(public_id, resource_type=resource_type)
                except Exception as e:
                    print(f"Admin Delete: Failed to delete {public_id} from Cloudinary: {e}")

    db.delete(profile)
    db.commit()
    return MessageResponse(message="Profile and associated data deleted successfully")


@router.post("/notifications/send", response_model=NotificationInDB)
def send_admin_notification(
        notification: NotificationCreate,
        db: Session = Depends(get_db)
):
    new_notification = Notification(**notification.model_dump())
    db.add(new_notification)
    db.commit()
    db.refresh(new_notification)
    return new_notification


# --- MATCHES ---
@router.get("/matches", response_model=List[MatchInDB])
def get_matches(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    matches = db.query(Match).offset(skip).limit(limit).all()
    return matches


@router.get("/matches/audit", response_model=List[MatchInDB])
def get_match_audit(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    # No is_audit field; return all matches or filter by another field if needed
    matches = db.query(Match).offset(skip).limit(limit).all()
    return matches


# --- RECOMMENDATIONS ---
@router.get("/recommendations", response_model=List[RecommendationInDB])
def get_recommendations(user_id: Optional[int] = None, recommended_user_id: Optional[int] = None,
                        status: Optional[str] = None, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    query = db.query(Recommendation)
    if user_id:
        query = query.filter(Recommendation.user_id == user_id)
    if recommended_user_id:
        query = query.filter(Recommendation.recommended_user_id == recommended_user_id)
    if status:
        query = query.filter(Recommendation.status == status)
    recommendations = query.offset(skip).limit(limit).all()
    return recommendations


@router.get("/recommendations/{user_id}", response_model=List[RecommendationInDB])
def get_recommendations_for_user(user_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    recommendations = db.query(Recommendation).filter(Recommendation.user_id == user_id).offset(skip).limit(limit).all()
    return recommendations


# --- ADMIN LIST ---
@router.get("/all", response_model=List[AdminInDB])
def list_admins(db: Session = Depends(get_db)):
    admins = db.query(Admin).all()
    return admins


# --- BLOCKED USERS ---
@router.get("/blocked-users", response_model=List[BlockedUserInDB])
def get_blocked_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    blocked_users = db.query(BlockedUser).offset(skip).limit(limit).all()
    return blocked_users


@router.post("/blocked-users", response_model=BlockedUserInDB)
def block_user_admin(blocker_user_id: int, blocked_user_id: int, reason: Optional[str] = None,
                     db: Session = Depends(get_db)):
    from datetime import datetime
    blocked_user = BlockedUser(
        blocker_user_id=blocker_user_id,
        blocked_user_id=blocked_user_id,
        reason=reason,
        created_at=datetime.utcnow()
    )
    db.add(blocked_user)
    db.commit()
    db.refresh(blocked_user)
    return blocked_user


@router.delete("/blocked-users/{block_id}", response_model=MessageResponse)
def unblock_user(block_id: int, db: Session = Depends(get_db)):
    blocked_user = db.query(BlockedUser).filter(BlockedUser.block_id == block_id).first()
    if not blocked_user:
        raise HTTPException(status_code=404, detail="Blocked user not found")
    db.delete(blocked_user)
    db.commit()
    return MessageResponse(message=f"Blocked user {block_id} deleted")

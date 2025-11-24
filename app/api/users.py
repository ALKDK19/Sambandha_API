from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.interaction import Match
from app.models.preference import Preference
from app.models.profile import Profile
from app.models.recommender import Recommendation
from app.models.security import BlockedUser
from app.models.user import User
from app.schemas.base import MessageResponse
from app.schemas.user import UserInDB, FcmTokenUpdate, ChangePasswordRequest
from utilities.logging_config import logger, security_logger
from utilities.rate_limiter import check_rate_limit
from utilities.security import get_current_user, verify_password, get_password_hash, active_user_ids_query

router = APIRouter()


@router.get("/me", response_model=UserInDB)
def read_current_user(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        request: Request = None
):
    # Add rate limiting and logging
    if request:
        check_rate_limit(request, max_requests=20, window_seconds=60)

    logger.info(f"User {current_user.user_id} accessing their profile")

    db_user = db.query(User).filter(User.user_id == current_user.user_id).first()
    if not db_user:
        security_logger.warning(f"User {current_user.user_id} not found in database")
        raise HTTPException(status_code=404, detail="User not found")
    return UserInDB.model_validate(db_user)


@router.get("/view/{user_id}", response_model=UserInDB)
def read_user(
        user_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        request: Request = None
):
    # Input validation
    if user_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    if request:
        check_rate_limit(request, max_requests=30, window_seconds=60)

    # Check if the user is blocked
    is_blocked = db.query(BlockedUser).filter(
        ((BlockedUser.blocker_user_id == current_user.user_id) &
         (BlockedUser.blocked_user_id == user_id)) |
        ((BlockedUser.blocker_user_id == user_id) &
         (BlockedUser.blocked_user_id == current_user.user_id))
    ).first()

    if is_blocked:
        raise HTTPException(status_code=403, detail="Access denied")

    db_user = db.query(User).filter(User.user_id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if user is active
    if not db_user.is_active:
        raise HTTPException(status_code=404, detail="User not found")

    logger.info(f"User {current_user.user_id} accessing profile of user {user_id}")
    return UserInDB.model_validate(db_user)


@router.post("/deactivate", status_code=status.HTTP_200_OK)
def deactivate_account(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        request: Request = None
):
    if request:
        check_rate_limit(request, max_requests=3, window_seconds=300)  # Strict rate limiting

    db_user = db.query(User).filter(User.user_id == current_user.user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    if not db_user.is_active:
        raise HTTPException(status_code=400, detail="Account already deactivated")

    db_user.is_active = False
    db_user.deactivated_by = "user"
    db.commit()

    security_logger.info(f"User {current_user.user_id} deactivated their account")

    return {"detail": "Account deactivated successfully", "logout": True}


@router.delete("/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    db_user = db.query(User).filter(User.user_id == current_user.user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    # Delete related Profile
    db.query(Profile).filter(Profile.user_id == db_user.user_id).delete()
    # Delete related Preference
    db.query(Preference).filter(Preference.user_id == db_user.user_id).delete()
    # Delete related Recommendations (as user or recommended_user)
    db.query(Recommendation).filter(
        (Recommendation.user_id == db_user.user_id) | (Recommendation.recommended_user_id == db_user.user_id)).delete()
    # Delete related Matches (as user1 or user2)
    db.query(Match).filter((Match.user1_id == db_user.user_id) | (Match.user2_id == db_user.user_id)).delete()
    # Delete related Notifications
    from app.models.engagement import Notification
    db.query(Notification).filter(Notification.user_id == db_user.user_id).delete()
    db.delete(db_user)
    db.commit()
    return


@router.post("/block/{user_id}", status_code=204)
def block_user(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="You cannot block yourself.")
    existing = db.query(BlockedUser).filter_by(blocker_user_id=current_user.user_id, blocked_user_id=user_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already blocked.")
    block = BlockedUser()
    block.blocker_user_id = current_user.user_id
    block.blocked_user_id = user_id
    db.add(block)
    db.commit()
    return


@router.post("/unblock/{user_id}", status_code=204)
def unblock_user(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    block = db.query(BlockedUser).filter_by(blocker_user_id=current_user.user_id, blocked_user_id=user_id).first()
    if not block:
        raise HTTPException(status_code=404, detail="Block not found.")
    db.delete(block)
    db.commit()
    return


@router.get("/blocked", response_model=List[UserInDB])
def get_blocked_users(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    blocked_relations = db.query(BlockedUser).filter_by(blocker_user_id=current_user.user_id).all()
    blocked_user_ids = [b.blocked_user_id for b in blocked_relations]
    if not blocked_user_ids:
        return []
    blocked_users = db.query(User).filter(User.user_id.in_(blocked_user_ids),
                                          User.user_id.in_(active_user_ids_query(db))).all()
    return [UserInDB.model_validate(u) for u in blocked_users]


@router.post("/me/fcm-token", response_model=MessageResponse)
def update_fcm_token(
        token_data: FcmTokenUpdate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Updates the FCM registration token for the current user.
    """
    current_user.fcm_token = token_data.fcm_token
    db.commit()

    # get fcm token from database to verify update
    updated_user = db.query(User).filter(User.user_id == current_user.user_id).first()
    if updated_user.fcm_token != token_data.fcm_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update FCM token."
        )

    logger.info(f"Updated FCM token for user {current_user.user_id}")
    return MessageResponse(message="FCM token updated successfully")


@router.post("/me/change-password", response_model=MessageResponse)
def change_current_user_password(
        request: ChangePasswordRequest,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Allows the currently authenticated user to change their password.
    """
    # 1. Verify the user's current password
    if not verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password."
        )

    # 2. Ensure the new password is not the same as the old one
    if verify_password(request.new_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password cannot be the same as the old password."
        )

    # 3. Hash and update the new password
    current_user.password_hash = get_password_hash(request.new_password)
    db.commit()

    return MessageResponse(message="Password updated successfully.")

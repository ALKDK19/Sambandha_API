from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.engagement import Notification
from app.models.interaction import Like, Match, Chat
from app.models.profile import Profile  # Import Profile
from app.models.user import User
from app.schemas.interaction import LikeCreate, LikeInDB, LikeReceivedResponse
from app.schemas.profile import ProfileSummary  # Import ProfileSummary
from app.schemas.user import UserInDB
from utilities.firebase_notifications import send_notification_to_user
from utilities.recsys.match_maker import MatchMaker
from utilities.security import get_current_user, active_user_ids_query

router = APIRouter()


@router.post("/", response_model=LikeInDB)
def create_like(
        like: LikeCreate,
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    # Check if a user likes themselves
    if like.liked_user_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="Cannot like yourself")

    # Check if like already exists
    existing_like = db.query(Like).filter(
        Like.liker_user_id == current_user.user_id,
        Like.liked_user_id == like.liked_user_id
    ).first()

    if existing_like:
        # if not interested, update status to disliked
        if like.like_type == 'dislike':
            existing_like.status = 'disliked'
            db.commit()
            db.refresh(existing_like)
            return existing_like

        # if like type in request and in db row are the same, delete the existing like (toggle off)
        if existing_like.like_type == like.like_type:
            # Toggle like (undo like)
            db.delete(existing_like)
            db.commit()
            return existing_like

        # if it's super like and existing is not, upgrade it to super like
        if like.like_type == 'super_like' and existing_like.like_type != 'super_like':
            existing_like.like_type = 'super_like'
            db.commit()
            db.refresh(existing_like)
            return existing_like

        # if it's just like and existing is super like, upgrade it to like
        if like.like_type == 'like' and existing_like.like_type == 'super_like':
            existing_like.like_type = 'like'
            db.commit()
            db.refresh(existing_like)
            return existing_like

    status = 'disliked' if like.is_not_interested is True else 'active'
    try:
        # Create like (instantiate then set attributes to avoid constructor kwarg warnings)
        new_like = Like()
        new_like.liker_user_id = current_user.user_id
        new_like.liked_user_id = like.liked_user_id
        new_like.like_type = like.like_type
        new_like.status = status
        db.add(new_like)
        # Make sure new_like gets a primary key / identity in the session
        # before any db.refresh or queries that depend on it.
        db.flush()

        # if it's a super like, then check if it is a mutual super like to create a match (with no score) if not exists
        if status == 'active' and like.like_type == 'super_like':
            # Check whether the other user has also super-liked the current user
            mutual_super = db.query(Like).filter(
                Like.liker_user_id == like.liked_user_id,
                Like.liked_user_id == current_user.user_id,
                Like.like_type == 'super_like',
                Like.status == 'active'
            ).first()

            if mutual_super:
                # check match with same users does not already exist
                existing_match = db.query(Match).filter(
                    ((Match.user1_id == current_user.user_id) & (Match.user2_id == like.liked_user_id)) |
                    ((Match.user1_id == like.liked_user_id) & (Match.user2_id == current_user.user_id)),
                    Match.match_status == 'active'
                ).first()

                # if the match already exists, just return the like
                if existing_match:
                    db.commit()
                    db.refresh(new_like)
                    return new_like

                # if not, check both of their profiles exist and are verified before creating a match
                user1_profile = db.query(Profile).filter(Profile.user_id == current_user.user_id).first()
                user2_profile = db.query(Profile).filter(Profile.user_id == like.liked_user_id).first()
                if not user1_profile or not user2_profile:
                    db.commit()
                    db.refresh(new_like)
                    return new_like
                if not user1_profile.is_verified or not user2_profile.is_verified:
                    db.commit()
                    db.refresh(new_like)
                    return new_like

                # Create a new match
                new_match = Match()
                new_match.user1_id = current_user.user_id
                new_match.user2_id = like.liked_user_id
                new_match.compatibility_score = None
                new_match.match_status = 'active'
                new_match.match_type = 'mutual_super_like'
                db.add(new_match)
                db.commit()
                db.refresh(new_match)

                # create chat with these users if not exists
                existing_chat = db.query(Chat).filter(
                    ((Chat.initiator_user_id == current_user.user_id) & (Chat.receiver_user_id == like.liked_user_id)) |
                    ((Chat.initiator_user_id == like.liked_user_id) & (Chat.receiver_user_id == current_user.user_id))
                ).first()

                if not existing_chat:
                    new_chat = Chat()
                    new_chat.match_id = new_match.match_id
                    new_chat.initiator_user_id = current_user.user_id
                    new_chat.receiver_user_id = like.liked_user_id
                    new_chat.state = 'active'  # Since it's a match, the chat can start as active
                    db.add(new_chat)
                    db.commit()
                    db.refresh(new_chat)

                # create notifications for both users about the new match
                new_notification_user1 = Notification()
                new_notification_user1.user_id = current_user.user_id
                new_notification_user1.notification_type = 'new_match'
                new_notification_user1.title = "It's a Match! 🎉"
                new_notification_user1.message_body = f"You and {user2_profile.first_name} have super-liked each other."
                new_notification_user1.related_entity_type = 'user'
                new_notification_user1.related_entity_id = like.liked_user_id
                db.add(new_notification_user1)

                new_notification_user2 = Notification()
                new_notification_user2.user_id = like.liked_user_id
                new_notification_user2.notification_type = 'new_match'
                new_notification_user2.title = "It's a Match! 🎉"
                new_notification_user2.message_body = f"You and {user1_profile.first_name} have super-liked each other."
                new_notification_user2.related_entity_type = 'user'
                new_notification_user2.related_entity_id = current_user.user_id
                db.add(new_notification_user2)

                db.commit()
                db.refresh(new_notification_user2)
                db.refresh(new_notification_user1)

                # Send notifications to both users
                try:
                    user1 = db.query(User).filter(User.user_id == current_user.user_id).first()
                    user2 = db.query(User).filter(User.user_id == like.liked_user_id).first()

                    if user1 and user2 and user1.profile and user2.profile:
                        notification_user1 = {
                            'notification_id': new_notification_user1.notification_id,
                            'user_id': user1.user_id,
                            'notification_type': new_notification_user1.notification_type,
                            'title': new_notification_user1.title,
                            'message_body': new_notification_user1.message_body,
                            'related_entity_type': new_notification_user1.related_entity_type,
                            'related_entity_id': new_notification_user1.related_entity_id,
                            'created_at': new_notification_user1.created_at.isoformat()
                        }
                        notification_user2 = {
                            'notification_id': new_notification_user2.notification_id,
                            'user_id': user2.user_id,
                            'notification_type': new_notification_user2.notification_type,
                            'title': new_notification_user2.title,
                            'message_body': new_notification_user2.message_body,
                            'related_entity_type': new_notification_user2.related_entity_type,
                            'related_entity_id': new_notification_user2.related_entity_id,
                            'created_at': new_notification_user2.created_at.isoformat()
                        }

                        print(notification_user1)
                        print(notification_user2)

                        send_notification_to_user(
                            user=user2,
                            title="It's a Match! 🎉",
                            body=f"You and {user1.profile.first_name} have super-liked each other.",
                            data=notification_user2
                        )
                        send_notification_to_user(
                            user=user1,
                            title="It's a Match! 🎉",
                            body=f"You and {user2.profile.first_name} have super-liked each other.",
                            data=notification_user1
                        )

                        print("==================================================")
                        print("Notifications sent for new match between ")
                        print("==================================================")
                except Exception:
                    pass
            elif status == 'active' and like.like_type == 'like':
                mm = MatchMaker(db)
                mm.create_matches_from_recs(user_id=current_user.user_id, limit=50)

        # Ensure the new object is committed/persistent before refresh
        db.commit()
        db.refresh(new_like)
        return new_like

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")


@router.get("/received", response_model=list[LikeReceivedResponse])
def get_received_likes(
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db),
        limit: int = 10,
        offset: int = 0
):
    # Exclude likers that the current user has previously disliked
    disliked_user_ids_query = db.query(Like.liked_user_id).filter(
        Like.liker_user_id == current_user.user_id,
        Like.status == 'disliked'
    ).subquery()

    # This query now fetches the entire Like object along with the related profile
    likes = db.query(Like).options(
        joinedload(Like.liker).joinedload(User.profile)
    ).filter(
        Like.liked_user_id == current_user.user_id,
        Like.status == 'active',
        Like.liker_user_id.notin_(disliked_user_ids_query)
    ).filter(
        Like.liker.has(User.is_active.is_(True))
    ).order_by(Like.created_at.desc()).offset(offset).limit(limit).all()

    response = []
    for like in likes:
        if like.liker and like.liker.profile:
            # We construct the new response object for each like
            response.append(
                LikeReceivedResponse(
                    liker_profile=like.liker.profile,
                    like_type=like.like_type
                )
            )
    return response


@router.get("/sent", response_model=List[ProfileSummary])  # FIX: Changed response model
def get_sent_likes(
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db),
        limit: int = 20,
        offset: int = 0
):
    # Build a query of users that the current user has actively liked
    liked_user_ids_query = db.query(Like.liked_user_id).filter(
        Like.liker_user_id == current_user.user_id,
        Like.status == 'active'
    )

    # Also exclude any users the current user has explicitly disliked
    disliked_user_ids_query = db.query(Like.liked_user_id).filter(
        Like.liker_user_id == current_user.user_id,
        Like.status == 'disliked'
    ).subquery()

    profiles = db.query(Profile).filter(
        Profile.user_id.in_(liked_user_ids_query),
        Profile.user_id != current_user.user_id,
        Profile.user_id.notin_(disliked_user_ids_query),
        Profile.user_id.in_(active_user_ids_query(db))
    ).order_by(Profile.profile_id.desc()).offset(offset).limit(limit).all()

    return profiles


@router.post("/dislike/{liked_user_id}", response_model=LikeInDB)
def dislike_user(
        liked_user_id: int,
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    # User cannot dislike themselves
    if liked_user_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="Cannot dislike yourself")

    # Find existing like
    existing_like = db.query(Like).filter(
        Like.liker_user_id == current_user.user_id,
        Like.liked_user_id == liked_user_id
    ).first()

    if not existing_like:
        raise HTTPException(status_code=400, detail="You must like the user before you can dislike them")
    if existing_like.status == "disliked":
        raise HTTPException(status_code=400, detail="Already disliked this user")

    # Set status to 'disliked'
    existing_like.status = "disliked"
    db.commit()
    db.refresh(existing_like)

    # Unmatch if a match exists between these users
    from app.models.interaction import Match
    match = db.query(Match).filter(
        ((Match.user1_id == current_user.user_id) & (Match.user2_id == liked_user_id)) |
        ((Match.user1_id == liked_user_id) & (Match.user2_id == current_user.user_id)),
        Match.match_status == 'active'
    ).first()
    if match:
        match.match_status = 'unmatched'
        db.commit()

    return existing_like

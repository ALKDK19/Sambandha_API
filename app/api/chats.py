from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.interaction import Chat, Match
from app.models.profile import Profile
from app.schemas.interaction import ChatWithUsers
from app.schemas.user import UserInDB
from utilities.security import get_current_user

router = APIRouter()


@router.get("/", response_model=List[ChatWithUsers])
def get_chats(
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db),
        limit: int = 10,
        offset: int = 0
):
    chats = db.query(Chat).filter(
        (Chat.initiator_user_id == current_user.user_id) |
        (Chat.receiver_user_id == current_user.user_id)
    ).offset(offset).limit(limit).all()
    chat_list = []
    for chat in chats:
        # fetch profiles for both users
        initiator_profile = db.query(Profile).filter(Profile.user_id == chat.initiator.user_id).first()
        receiver_profile = db.query(Profile).filter(Profile.user_id == chat.receiver.user_id).first()

        chat_list.append(ChatWithUsers(
            chat_id=chat.chat_id,
            match_id=chat.match_id,
            initiator_user_id=chat.initiator.user_id,
            receiver_user_id=chat.receiver.user_id,
            state=chat.state,
            created_at=chat.created_at,
            match=chat.match if hasattr(chat, 'match') else None,
            users=[initiator_profile, receiver_profile]
        ))
    return chat_list


@router.get("/{chat_id}", response_model=ChatWithUsers)
def get_chat(
        chat_id: int,
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    chat = db.query(Chat).filter(
        Chat.chat_id == chat_id,
        (Chat.initiator_user_id == current_user.user_id) |
        (Chat.receiver_user_id == current_user.user_id)
    ).first()

    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    # fetch profiles for both users
    initiator_profile = db.query(Profile).filter(Profile.user_id == chat.initiator.user_id).first()
    receiver_profile = db.query(Profile).filter(Profile.user_id == chat.receiver.user_id).first()

    return ChatWithUsers(
        chat_id=chat.chat_id,
        match_id=chat.match_id,
        initiator_user_id=chat.initiator.user_id,
        receiver_user_id=chat.receiver.user_id,
        state=chat.state,
        created_at=chat.created_at,
        match=chat.match if hasattr(chat, 'match') else None,
        users=[initiator_profile, receiver_profile]
    )


@router.delete("/{chat_id}")
def delete_chat(
        chat_id: int,
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    chat = db.query(Chat).filter(
        Chat.chat_id == chat_id,
        (Chat.initiator_user_id == current_user.user_id) |
        (Chat.receiver_user_id == current_user.user_id)
    ).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    # Delete all messages in the chat
    db.query(Chat.messages.property.mapper.class_).filter_by(chat_id=chat_id).delete()
    db.delete(chat)
    db.commit()
    return {"message": "Chat and its messages deleted successfully"}


@router.post("/find-or-create/{other_user_id}", response_model=ChatWithUsers)
def find_or_create_chat(
        other_user_id: int,
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    if other_user_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="Cannot create a chat with yourself.")

    # Check for existing chat in either direction
    chat = db.query(Chat).filter(
        or_(
            and_(Chat.initiator_user_id == current_user.user_id, Chat.receiver_user_id == other_user_id),
            and_(Chat.initiator_user_id == other_user_id, Chat.receiver_user_id == current_user.user_id)
        )
    ).first()

    if chat:
        # get profiles for both users
        initiator_profile = db.query(Profile).filter(Profile.user_id == chat.initiator.user_id).first()
        receiver_profile = db.query(Profile).filter(Profile.user_id == chat.receiver.user_id).first()

        return ChatWithUsers(
            chat_id=chat.chat_id,
            match_id=chat.match_id,
            initiator_user_id=chat.initiator_user_id,
            receiver_user_id=chat.receiver_user_id,
            state=chat.state,
            created_at=chat.created_at,
            match=chat.match if hasattr(chat, 'match') else None,
            users=[initiator_profile, receiver_profile]
        )

    match = db.query(Match).filter(
        Match.match_status == 'active',
        or_(
            and_(Match.user1_id == current_user.user_id, Match.user2_id == other_user_id),
            and_(Match.user1_id == other_user_id, Match.user2_id == current_user.user_id)
        )
    ).first()

    # Create a new chat based on the active match existence
    new_chat = Chat(
        match_id=match.match_id if match else None,
        initiator_user_id=current_user.user_id,
        receiver_user_id=other_user_id,
        state='active' if match else 'request'
    )
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)

    # get profiles for both users
    initiator_profile = db.query(Profile).filter(Profile.user_id == new_chat.initiator.user_id).first()
    receiver_profile = db.query(Profile).filter(Profile.user_id == new_chat.receiver.user_id).first()

    return ChatWithUsers(
        chat_id=new_chat.chat_id,
        match_id=new_chat.match_id,
        initiator_user_id=new_chat.initiator_user_id,
        receiver_user_id=new_chat.receiver_user_id,
        state=new_chat.state,
        created_at=new_chat.created_at,
        match=new_chat.match if hasattr(new_chat, 'match') else None,
        users=[initiator_profile, receiver_profile]
    )

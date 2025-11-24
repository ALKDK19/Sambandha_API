import asyncio
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.interaction import Chat, Message
from app.models.security import BlockedUser
from app.models.user import User
from app.schemas.base import MessageResponse
from app.schemas.interaction import MessageCreate, MessageWithUsers, MessageInResponse
from app.schemas.user import UserInDB
from utilities.firebase_notifications import send_notification_to_user
from utilities.security import get_current_user

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, WebSocket] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: int):
        self.active_connections.pop(user_id, None)

    async def send_personal_message(self, user_id: int, message: dict):
        websocket = self.active_connections.get(user_id)
        if websocket:
            await websocket.send_json(message)

    async def broadcast(self, user_ids: list[int], message: dict):
        for uid in user_ids:
            await self.send_personal_message(uid, message)


manager = ConnectionManager()

# Add limits: max consecutive messages in the 'request' state and max message length
MAX_CONSECUTIVE_MESSAGES = 2
MAX_MESSAGE_LENGTH = 50


@router.post("/", response_model=MessageInResponse)
async def create_message(
        message: MessageCreate,
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    # Validate message length (apply when content is present)
    if message.message_content and len(message.message_content.strip()) > MAX_MESSAGE_LENGTH:
        raise HTTPException(status_code=400, detail=f"Message cannot exceed {MAX_MESSAGE_LENGTH} characters")

    # Check if a chat exists between users
    chat = db.query(Chat).filter(
        or_(
            and_(Chat.initiator_user_id == current_user.user_id, Chat.receiver_user_id == message.receiver_user_id),
            and_(Chat.initiator_user_id == message.receiver_user_id, Chat.receiver_user_id == current_user.user_id)
        )
    ).first()

    if not chat:
        # Create a chat with state 'request' if not matched
        chat = Chat(
            initiator_user_id=current_user.user_id,
            receiver_user_id=message.receiver_user_id,
            state='request'
        )
        db.add(chat)
        db.commit()
        db.refresh(chat)

    # Check if the receiver is blocked
    blocked = db.query(BlockedUser).filter(
        ((BlockedUser.blocker_user_id == current_user.user_id) &
         (BlockedUser.blocked_user_id == message.receiver_user_id)) |
        ((BlockedUser.blocker_user_id == message.receiver_user_id) &
         (BlockedUser.blocked_user_id == current_user.user_id))
    ).first()

    if blocked:
        raise HTTPException(status_code=403, detail="Cannot message blocked user")

    # Check if the receiver is deactivated
    receiver = db.query(User).filter(User.user_id == message.receiver_user_id).first()
    if not receiver or not receiver.is_active:
        raise HTTPException(status_code=403, detail="Cannot message a deactivated user")

    # Messaging logic for chat state: enforce max consecutive messages when in 'request' state
    if chat.state == 'request':
        # Look at the last messages (up to MAX_CONSECUTIVE_MESSAGES) and count consecutive sends by this user
        recent_msgs = db.query(Message).filter(
            Message.chat_id == chat.chat_id
        ).order_by(Message.sent_at.desc()).limit(MAX_CONSECUTIVE_MESSAGES).all()

        consecutive = 0
        for m in recent_msgs:
            if m.sender_user_id == current_user.user_id:
                consecutive += 1
            else:
                break

        if consecutive >= MAX_CONSECUTIVE_MESSAGES:
            raise HTTPException(status_code=403,
                                detail=f"You can only send {MAX_CONSECUTIVE_MESSAGES} consecutive messages until the "
                                       f"recipient replies.")

    # Create and store the message
    new_message = Message(
        chat_id=chat.chat_id,
        sender_user_id=current_user.user_id,
        receiver_user_id=message.receiver_user_id,
        message_content=message.message_content,
        message_type=message.message_type
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    # Send push notification
    sender = db.query(User).filter(User.user_id == current_user.user_id).first()
    receiver = db.query(User).filter(User.user_id == message.receiver_user_id).first()

    if receiver and sender:
        send_notification_to_user(
            user=receiver,
            title=f"New message from {sender.profile.first_name}",  # Assumes profile exists
            body=new_message.message_content,
            data={
                "type": "new_message",
                "id": str(chat.chat_id),
                # You might need to send other user info for the app to navigate properly
            }
        )

    # Real-time delivery if the recipient is online
    asyncio.create_task(
        manager.send_personal_message(message.receiver_user_id, MessageWithUsers.from_orm(new_message).dict()))

    return new_message


@router.get("/chat/{chat_id}", response_model=List[MessageInResponse])
def get_chat_messages(
        chat_id: int,
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db),
        limit: int = 100,
        offset: int = 0
):
    # Check if chat exists and user is part of it
    chat = db.query(Chat).filter(
        Chat.chat_id == chat_id,
        (Chat.initiator_user_id == current_user.user_id) |
        (Chat.receiver_user_id == current_user.user_id)
    ).first()

    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    messages = db.query(Message).filter(
        Message.chat_id == chat_id,
        Message.sender.has(User.is_active == True),
        Message.receiver.has(User.is_active == True)
    ).order_by(Message.sent_at.desc()).offset(offset).limit(limit).all()
    return messages


@router.delete("/{message_id}")
def delete_message(
        message_id: int,
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    message = db.query(Message).filter(
        Message.message_id == message_id,
        Message.sender_user_id == current_user.user_id
    ).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found or not owned by user")
    db.delete(message)
    db.commit()
    return {"message": "Message deleted successfully"}


@router.post("/chat/{chat_id}/read", response_model=MessageResponse)
def mark_messages_as_read(
        chat_id: int,
        current_user: UserInDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Marks all unread messages in a chat for the current user as read."""
    chat = db.query(Chat).filter(
        Chat.chat_id == chat_id,
        ((Chat.initiator_user_id == current_user.user_id) | (Chat.receiver_user_id == current_user.user_id))
    ).first()

    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found or access denied.")

    db.query(Message).filter(
        Message.chat_id == chat_id,
        Message.receiver_user_id == current_user.user_id,
        Message.read_at.is_(None)
    ).update({"read_at": datetime.utcnow()}, synchronize_session=False)

    db.commit()
    return MessageResponse(message="Messages marked as read.")


@router.websocket("/ws/chat/{chat_id}")
async def websocket_chat(websocket: WebSocket, chat_id: int, db: Session = Depends(get_db)):
    # Authenticate user (simple token in query for demo, use secure auth in production)
    token = websocket.query_params.get("token")
    user = db.query(User).filter(User.auth_token == token).first() if token else None
    if not user:
        await websocket.close(code=1008)
        return
    await manager.connect(user.user_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # Extract message content and type
            message_content = data.get("message_content", "")
            message_type = data.get("message_type", "text")

            # Validate message length
            if message_content and len(message_content.strip()) > MAX_MESSAGE_LENGTH:
                await websocket.send_json({"error": f"Message cannot exceed {MAX_MESSAGE_LENGTH} characters"})
                continue

            # Validate chat and recipient
            chat = db.query(Chat).filter(Chat.chat_id == chat_id).first()
            if not chat or (user.user_id not in [chat.initiator_user_id, chat.receiver_user_id]):
                await websocket.send_json({"error": "Invalid chat"})
                continue
            receiver_id = chat.receiver_user_id if chat.initiator_user_id == user.user_id else chat.initiator_user_id

            # Enforce consecutive message limit in 'request' state
            if chat.state == 'request':
                recent_msgs = db.query(Message).filter(
                    Message.chat_id == chat.chat_id
                ).order_by(Message.sent_at.desc()).limit(MAX_CONSECUTIVE_MESSAGES).all()

                consecutive = 0
                for m in recent_msgs:
                    if m.sender_user_id == user.user_id:
                        consecutive += 1
                    else:
                        break
                if consecutive >= MAX_CONSECUTIVE_MESSAGES:
                    await websocket.send_json({
                        "error": f"You can only send {MAX_CONSECUTIVE_MESSAGES} consecutive messages until the recipient replies."})
                    continue

            # Save message to DB
            msg = Message(
                chat_id=chat_id,
                sender_user_id=user.user_id,
                receiver_user_id=receiver_id,
                message_content=message_content,
                message_type=message_type,
            )
            db.add(msg)
            db.commit()
            db.refresh(msg)
            msg_data = {
                "message_id": msg.message_id,
                "chat_id": chat_id,
                "sender_user_id": user.user_id,
                "receiver_user_id": receiver_id,
                "message_content": msg.message_content,
                "created_at": str(msg.sent_at)
            }
            # Send it to receiver if online
            await manager.send_personal_message(receiver_id, msg_data)
            # Echo to sender
            await websocket.send_json(msg_data)
    except WebSocketDisconnect:
        manager.disconnect(user.user_id)

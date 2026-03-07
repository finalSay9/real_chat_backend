from fastapi import FastAPI, WebSocket,WebSocketDisconnect,Depends,Query,APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from sqlalchemy.orm import selectinload
import json
import logging
from database import  SessionLocal
from models import User, Room, Message, room_members, UserStatus
from schemas import WSIncoming
from security import decode_token
from ws_manager import manager
from dependency import get_db





logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws",
             tags=["websocket"])

async def _get_ws_user(token: str | None, db: AsyncSession) -> User | None:
    """Authenticate a WebSocket connection via token query param."""
    if not token:
        return None
    user_id = decode_token(token)
    if not user_id:
        return None
    result = await db.execute(
        select(User).where(User.id == user_id, User.is_active == True)
    )
    return result.scalar_one_or_none()    

#creating a member
async def _is_member(room_id: str, user_id: str, db: AsyncSession) -> bool:
    result = await db.execute(
        select(room_members).where(
            room_members.c.room_id == room_id,
            room_members.c.user_id == user_id,
        )
    )
    return result.first() is not None


@router.websocket("/rooms/{room_id}")
async def websocket_room(
    websocket: WebSocket,
    room_id: str,
    token: str | None = Query(None),
):
    """
    WebSocket endpoint for real-time room messaging.

    Client connects to: ws://localhost:8000/ws/rooms/{room_id}?token=<jwt>

    Incoming message shapes:
        { "type": "message",  "content": "Hello!" }
        { "type": "typing",   "is_typing": true }

    Outgoing event shapes:
        { "type": "message",        "data": { ...MessagePublic } }
        { "type": "message_deleted","data": { "message_id": "..." } }
        { "type": "typing",         "data": { "user_id": "...", "display_name": "...", "is_typing": true } }
        { "type": "user_join",      "data": { "user_id": "...", "display_name": "..." } }
        { "type": "user_leave",     "data": { "user_id": "...", "display_name": "..." } }
        { "type": "error",          "data": { "message": "..." } }
    """
    # ── Auth ──────────────────────────────────────────────────────────────────
    async with SessionLocal() as db:
        user = await _get_ws_user(token, db)
        if not user:
            await websocket.close(code=4001, reason="Unauthorized")
            return

        # ── Room check ────────────────────────────────────────────────────────
        result = await db.execute(select(Room).where(Room.id == room_id))
        room = result.scalar_one_or_none()
        if not room:
            await websocket.close(code=4004, reason="Room not found")
            return

        is_member = await _is_member(room_id, user.id, db)
        if not is_member:
            # Auto-join public rooms
            if not room.is_private:
                await db.execute(
                    insert(room_members).values(user_id=user.id, room_id=room_id)
                )
                await db.commit()
            else:
                await websocket.close(code=4003, reason="Not a member")
                return

        # ── Connect ───────────────────────────────────────────────────────────
        await manager.connect(room_id, user.id, websocket)

        # Mark user online
        user.status = UserStatus.online
        await db.commit()

    # Notify others that user joined
    await manager.broadcast(
        room_id,
        {
            "type": "user_join",
            "data": {"user_id": user.id, "display_name": user.display_name},
        },
        exclude=user.id,
    )

    # ── Message loop ──────────────────────────────────────────────────────────
    try:
        while True:
            raw = await websocket.receive_text()

            try:
                payload = WSIncoming.model_validate_json(raw)
            except Exception:
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": "Invalid message format"},
                })
                continue

            # ── Handle: chat message ─────────────────────────────────────────
            if payload.type == "message":
                if not payload.content or not payload.content.strip():
                    continue

                async with SessionLocal() as db:
                    msg = Message(
                        room_id=room_id,
                        sender_id=user.id,
                        content=payload.content.strip(),
                    )
                    db.add(msg)
                    await db.commit()
                    await db.refresh(msg)

                    result = await db.execute(
                        select(Message)
                        .options(selectinload(Message.sender))
                        .where(Message.id == msg.id)
                    )
                    msg = result.scalar_one()

                event = {
                    "type": "message",
                    "data": {
                        "id": msg.id,
                        "room_id": msg.room_id,
                        "sender_id": msg.sender_id,
                        "sender_name": msg.sender.display_name,
                        "content": msg.content,
                        "status": msg.status,
                        "edited": msg.edited,
                        "created_at": msg.created_at.isoformat(),
                    },
                }

                # Echo back to sender as confirmation
                await manager.send_to(room_id, user.id, {**event, "data": {**event["data"], "status": "delivered"}})
                # Broadcast to everyone else
                await manager.broadcast(room_id, event, exclude=user.id)

            # ── Handle: typing indicator ─────────────────────────────────────
            elif payload.type == "typing":
                await manager.broadcast(
                    room_id,
                    {
                        "type": "typing",
                        "data": {
                            "user_id": user.id,
                            "display_name": user.display_name,
                            "is_typing": bool(payload.is_typing),
                        },
                    },
                    exclude=user.id,
                )

    except WebSocketDisconnect:
        pass

    finally:
        manager.disconnect(room_id, user.id)

        # If user has no more active rooms, mark offline
        if manager.user_room_count(user.id) == 0:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(User).where(User.id == user.id))
                u = result.scalar_one_or_none()
                if u:
                    u.status = UserStatus.offline
                    await db.commit()

        await manager.broadcast(
            room_id,
            {
                "type": "user_leave",
                "data": {"user_id": user.id, "display_name": user.display_name},
            },
        )
        logger.info(f"{user.display_name} left room {room_id}")


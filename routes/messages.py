from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from database import get_db
from models import User, Room, Message, room_members
from schemas import MessageCreate, MessagePublic, MessageList
from auth import get_current_user
from ws_manager import manager


router = APIRouter(prefix="/rooms/{room_id}/messages", tags=["messages"])


async def _assert_member(room_id: str, user_id: str, db: AsyncSession):
    result = await db.execute(
        select(room_members).where(
            room_members.c.room_id == room_id,
            room_members.c.user_id == user_id,
        )
    )
    if not result.first():
        raise HTTPException(status_code=403, detail="Not a member of this room")




#to schema fucntio

def _to_schema(msg: Message) -> MessagePublic:
    return MessagePublic(
        id=msg.id,
        room_id=msg.room_id,
        sender_id=msg.sender_id,
        sender_name=msg.sender.display_name if msg.sender else "Unknown",
        content=msg.content,
        status=msg.status,
        edited=msg.edited,
        created_at=msg.created_at,
    )


@router.get("", response_model=MessageList)
async def list_messages(
    room_id: str,
    limit: int = Query(50, ge=1, le=100),
    before: str | None = Query(None, description="Message ID cursor for pagination"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _assert_member(room_id, current_user.id, db)

    q = (
        select(Message)
        .options(selectinload(Message.sender))
        .where(Message.room_id == room_id, Message.deleted == False)
        .order_by(Message.created_at.desc())
        .limit(limit + 1)
    )

    if before:
        # Cursor pagination — get messages older than `before` message
        cursor_result = await db.execute(select(Message).where(Message.id == before))
        cursor_msg = cursor_result.scalar_one_or_none()
        if cursor_msg:
            q = q.where(Message.created_at < cursor_msg.created_at)

    result = await db.execute(q)
    msgs = result.scalars().all()

    has_more = len(msgs) > limit
    msgs = msgs[:limit]
    msgs.reverse()  # return chronological order

    total_result = await db.execute(
        select(func.count()).where(Message.room_id == room_id, Message.deleted == False)
    )
    total = total_result.scalar()

    return MessageList(
        messages=[_to_schema(m) for m in msgs],
        total=total,
        has_more=has_more,
    )




@router.post("", response_model=MessagePublic, status_code=201)
async def send_message(
    room_id: str,
    body: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _assert_member(room_id, current_user.id, db)

    msg = Message(
        room_id=room_id,
        sender_id=current_user.id,
        content=body.content,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    # Reload with sender relationship
    result = await db.execute(
        select(Message).options(selectinload(Message.sender)).where(Message.id == msg.id)
    )
    msg = result.scalar_one()

    schema = _to_schema(msg)

    # Broadcast to all room members via WebSocket
    await manager.broadcast(
        room_id,
        {
            "type": "message",
            "data": schema.model_dump(mode="json"),
        },
        exclude=current_user.id,
    )

    return schema


@router.delete("/{message_id}", status_code=204)
async def delete_message(
    room_id: str,
    message_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Message).where(Message.id == message_id, Message.room_id == room_id)
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    if msg.sender_id != current_user.id:
        raise HTTPException(status_code=403, detail="Can only delete your own messages")

    msg.deleted = True
    await db.commit()

    await manager.broadcast(
        room_id,
        {"type": "message_deleted", "data": {"message_id": message_id}},
    )

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, insert, delete
from sqlalchemy.orm import selectinload

from dependency import get_db
from models import User, Room, Message, room_members, RoomType
from schemas import RoomCreate, RoomPublic, RoomWithLastMessage, UserPublic
from security import get_current_user

router = APIRouter(prefix="/rooms", tags=["rooms"])


async def _room_or_404(room_id: str, db: AsyncSession) -> Room:
    result = await db.execute(
        select(Room).options(selectinload(Room.members)).where(Room.id == room_id)
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


def _is_member(room: Room, user_id: str) -> bool:
    return any(m.id == user_id for m in room.members)


# ─── CRUD ────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[RoomWithLastMessage])
async def list_rooms(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all rooms the current user is a member of."""
    result = await db.execute(
        select(Room)
        .join(room_members, room_members.c.room_id == Room.id)
        .where(room_members.c.user_id == current_user.id)
        .options(selectinload(Room.members))
    )
    rooms = result.scalars().all()

    out = []
    for room in rooms:
        # Get last message
        msg_result = await db.execute(
            select(Message)
            .where(Message.room_id == room.id, Message.deleted == False)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        last = msg_result.scalar_one_or_none()

        out.append(RoomWithLastMessage(
            id=room.id,
            name=room.name,
            description=room.description,
            type=room.type,
            is_private=room.is_private,
            created_by=room.created_by,
            created_at=room.created_at,
            member_count=len(room.members),
            last_message=last.content if last else None,
            last_message_at=last.created_at if last else None,
        ))
    return out


@router.post("", response_model=RoomPublic, status_code=201)
async def create_room(
    body: RoomCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    room = Room(
        name=body.name,
        description=body.description,
        type=body.type,
        is_private=body.is_private,
        created_by=current_user.id,
    )
    db.add(room)
    await db.flush()  # get room.id

    # Auto-add creator as admin member
    await db.execute(
        insert(room_members).values(
            user_id=current_user.id,
            room_id=room.id,
            is_admin=True,
        )
    )
    await db.commit()
    await db.refresh(room)
    return RoomPublic(
        id=room.id, name=room.name, description=room.description,
        type=room.type, is_private=room.is_private,
        created_by=room.created_by, created_at=room.created_at,
        member_count=1,
    )


@router.get("/{room_id}", response_model=RoomPublic)
async def get_room(
    room_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    room = await _room_or_404(room_id, db)
    if room.is_private and not _is_member(room, current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    return RoomPublic(
        id=room.id, name=room.name, description=room.description,
        type=room.type, is_private=room.is_private,
        created_by=room.created_by, created_at=room.created_at,
        member_count=len(room.members),
    )


@router.post("/{room_id}/join", status_code=204)
async def join_room(
    room_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    room = await _room_or_404(room_id, db)
    if room.is_private:
        raise HTTPException(status_code=403, detail="Room is private — you need an invite")
    if _is_member(room, current_user.id):
        return  # already a member, no-op

    await db.execute(
        insert(room_members).values(user_id=current_user.id, room_id=room_id)
    )
    await db.commit()


@router.post("/{room_id}/leave", status_code=204)
async def leave_room(
    room_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await db.execute(
        delete(room_members).where(
            room_members.c.user_id == current_user.id,
            room_members.c.room_id == room_id,
        )
    )
    await db.commit()


@router.get("/{room_id}/members", response_model=list[UserPublic])
async def get_members(
    room_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    room = await _room_or_404(room_id, db)
    if not _is_member(room, current_user.id):
        raise HTTPException(status_code=403, detail="Not a member")
    return room.members
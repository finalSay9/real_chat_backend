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
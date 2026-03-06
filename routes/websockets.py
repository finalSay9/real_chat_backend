from fastapi import FastAPI, Websocket,WebsocketDisconnect,Depends,Query,APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from sqlalchemy.orm import selectinload
import json
import logging
from database import get_db, SessionLocal
from models import User, Room, Message, room_members, UserStatus
from schemas import WSIncoming
from auth import decode_token
from ws_manager import manager





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





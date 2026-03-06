from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from database import get_db
from models import User, Room, Message, room_members
from schemas import MessageCreate, MessagePublic, MessageList
from auth import get_current_user
from ws_manager import manager
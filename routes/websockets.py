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





router = APIRouter(
    prefix='websocket',
    tags=['websocket']
)





from fastapi import FastAPI, Websocket,WebsocketDisconnect,Depends,Query,APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert





router = APIRouter(
    prefix='websocket',
    tags=['websocket']
)





from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from models import UserStatus, RoomType, MessageStatus


# ─── Auth ─────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=6)
    display_name: str = Field(..., min_length=1, max_length=100)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ─── Users ────────────────────────────────────────────────────────────────────

class UserPublic(BaseModel):
    id: str
    username: str
    display_name: str
    status: UserStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)


class StatusUpdate(BaseModel):
    status: UserStatus


# ─── Rooms ────────────────────────────────────────────────────────────────────

class RoomCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    type: RoomType = RoomType.channel
    is_private: bool = False


class RoomPublic(BaseModel):
    id: str
    name: str
    description: Optional[str]
    type: RoomType
    is_private: bool
    created_by: Optional[str]
    created_at: datetime
    member_count: int = 0

    model_config = {"from_attributes": True}


class RoomWithLastMessage(RoomPublic):
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None
    unread_count: int = 0


# ─── Messages ─────────────────────────────────────────────────────────────────

class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)


class MessagePublic(BaseModel):
    id: str
    room_id: str
    sender_id: str
    sender_name: str
    content: str
    status: MessageStatus
    edited: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageList(BaseModel):
    messages: List[MessagePublic]
    total: int
    has_more: bool


# ─── WebSocket events ─────────────────────────────────────────────────────────

class WSEventType(str):
    MESSAGE = "message"
    MESSAGE_DELETED = "message_deleted"
    TYPING = "typing"
    USER_JOIN = "user_join"
    USER_LEAVE = "user_leave"
    STATUS_CHANGE = "status_change"
    ERROR = "error"


class WSIncoming(BaseModel):
    """Shape of messages sent FROM client TO server over WS."""
    type: str
    content: Optional[str] = None    # for type=message
    is_typing: Optional[bool] = None  # for type=typing


class WSOutgoing(BaseModel):
    """Shape of messages sent FROM server TO client over WS."""
    type: str
    data: dict
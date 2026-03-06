from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey,
    Text, Enum as SAEnum, Integer, Table
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from database import Base


def gen_uuid():
    return str(uuid.uuid4())


# ─── Association table: room members ─────────────────────────────────────────

room_members = Table(
    "room_members",
    Base.metadata,
    Column("user_id", String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("room_id", String, ForeignKey("rooms.id", ondelete="CASCADE"), primary_key=True),
    Column("joined_at", DateTime(timezone=True), server_default=func.now()),
    Column("is_admin", Boolean, default=False),
)


# ─── Enums ────────────────────────────────────────────────────────────────────

class UserStatus(str, enum.Enum):
    online = "online"
    away = "away"
    offline = "offline"


class RoomType(str, enum.Enum):
    channel = "channel"
    dm = "dm"


class MessageStatus(str, enum.Enum):
    sent = "sent"
    delivered = "delivered"
    read = "read"


# ─── Models ───────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    username = Column(String(50), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    hashed_password = Column(String, nullable=False)
    status = Column(SAEnum(UserStatus), default=UserStatus.offline)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    rooms = relationship("Room", secondary=room_members, back_populates="members")
    messages = relationship("Message", back_populates="sender", cascade="all, delete-orphan")


class Room(Base):
    __tablename__ = "rooms"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    type = Column(SAEnum(RoomType), default=RoomType.channel)
    is_private = Column(Boolean, default=False)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    members = relationship("User", secondary=room_members, back_populates="rooms")
    messages = relationship("Message", back_populates="room", cascade="all, delete-orphan",
                            order_by="Message.created_at")
    creator = relationship("User", foreign_keys=[created_by])


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=gen_uuid)
    room_id = Column(String, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    status = Column(SAEnum(MessageStatus), default=MessageStatus.sent)
    edited = Column(Boolean, default=False)
    deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    room = relationship("Room", back_populates="messages")
    sender = relationship("User", back_populates="messages")
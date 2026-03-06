from fastapi import WebSocket
from typing import Dict, Set
import json
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages active WebSocket connections grouped by room.

    Structure:
        _rooms: { room_id: { user_id: WebSocket } }
    """

    def __init__(self):
        self._rooms: Dict[str, Dict[str, WebSocket]] = {}

    # ─── Connection lifecycle ─────────────────────────────────────────────────

    async def connect(self, room_id: str, user_id: str, ws: WebSocket):
        await ws.accept()
        if room_id not in self._rooms:
            self._rooms[room_id] = {}
        self._rooms[room_id][user_id] = ws
        logger.info(f"User {user_id} connected to room {room_id}")

    def disconnect(self, room_id: str, user_id: str):
        if room_id in self._rooms:
            self._rooms[room_id].pop(user_id, None)
            if not self._rooms[room_id]:
                del self._rooms[room_id]
        logger.info(f"User {user_id} disconnected from room {room_id}")

    # ─── Sending ──────────────────────────────────────────────────────────────

    async def send_to(self, room_id: str, user_id: str, payload: dict):
        """Send to a single user in a room."""
        ws = self._rooms.get(room_id, {}).get(user_id)
        if ws:
            try:
                await ws.send_json(payload)
            except Exception as e:
                logger.warning(f"Failed to send to {user_id}: {e}")
                self.disconnect(room_id, user_id)

    async def broadcast(self, room_id: str, payload: dict, exclude: str | None = None):
        """Broadcast to all users in a room, optionally excluding one."""
        room_conns = dict(self._rooms.get(room_id, {}))
        for uid, ws in room_conns.items():
            if uid == exclude:
                continue
            try:
                await ws.send_json(payload)
            except Exception as e:
                logger.warning(f"Broadcast error for {uid}: {e}")
                self.disconnect(room_id, uid)

    async def broadcast_all(self, payload: dict, exclude: str | None = None):
        """Broadcast to every connected user across all rooms (e.g. status change)."""
        seen: Set[str] = set()
        for room_id, conns in dict(self._rooms).items():
            for uid, ws in dict(conns).items():
                if uid == exclude or uid in seen:
                    continue
                seen.add(uid)
                try:
                    await ws.send_json(payload)
                except Exception as e:
                    logger.warning(f"Global broadcast error for {uid}: {e}")
                    self.disconnect(room_id, uid)

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def online_users(self, room_id: str) -> Set[str]:
        return set(self._rooms.get(room_id, {}).keys())

    def user_room_count(self, user_id: str) -> int:
        return sum(1 for conns in self._rooms.values() if user_id in conns)


# Singleton — import this everywhere
manager = ConnectionManager()
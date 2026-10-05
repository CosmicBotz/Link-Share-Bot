"""
database/mongodb.py
~~~~~~~~~~~~~~~~~~~
Async MongoDB wrapper.

Collections:
  users    — {_id, joined}
  channels — {_id, name, added, req_mode, req_timer, link_count}
  banned   — {_id (user_id), reason, banned_by, banned_at}

Global timer stored as channels doc with _id="__global__".
"""
import time
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient

from config import DB_NAME, DB_URL, LOGGER

logger = LOGGER(__name__)

_GLOBAL_TIMER_ID = "__global__"


class _Database:

    def __init__(self):
        self._client:   Optional[AsyncIOMotorClient] = None
        self._db       = None
        self._users    = None
        self._channels = None
        self._banned   = None
        self._settings = None

    # ── Connection ────────────────────────────────────────────────────────────

    def connect(self):
        self._client   = AsyncIOMotorClient(DB_URL)
        self._db       = self._client[DB_NAME]
        self._users    = self._db["users"]
        self._channels = self._db["channels"]
        self._banned   = self._db["banned"]
        self._settings = self._db["bot_settings"]
        logger.info("Connected to MongoDB '%s'.", DB_NAME)

    # ── User methods ──────────────────────────────────────────────────────────

    async def add_user(self, user_id: int) -> bool:
        if await self._users.find_one({"_id": user_id}):
            return False
        await self._users.insert_one({"_id": user_id, "joined": int(time.time())})
        return True

    async def is_user_exist(self, user_id: int) -> bool:
        return bool(await self._users.find_one({"_id": user_id}))

    async def total_users(self) -> int:
        return await self._users.count_documents({})

    async def get_all_users(self) -> list[int]:
        return [doc["_id"] async for doc in self._users.find({}, {"_id": 1})]

    async def remove_user(self, user_id: int) -> bool:
        result = await self._users.delete_one({"_id": user_id})
        return result.deleted_count > 0

    # ── Ban methods ───────────────────────────────────────────────────────────

    async def ban_user(self, user_id: int, reason: str = "", banned_by: int = 0) -> None:
        await self._banned.update_one(
            {"_id": user_id},
            {"$set": {
                "reason":    reason,
                "banned_by": banned_by,
                "banned_at": int(time.time()),
            }},
            upsert=True,
        )

    async def unban_user(self, user_id: int) -> bool:
        result = await self._banned.delete_one({"_id": user_id})
        return result.deleted_count > 0

    async def is_user_banned(self, user_id: int) -> bool:
        return bool(await self._banned.find_one({"_id": user_id}))

    async def get_all_banned(self) -> list[dict]:
        return [doc async for doc in self._banned.find({})]

    async def total_banned(self) -> int:
        return await self._banned.count_documents({})

    # ── Channel methods ───────────────────────────────────────────────────────

    def _channel_filter(self, channel_id) -> dict:
        """Match channel by int ID, str ID, or fallback chat_id/channel_id fields."""
        try:
            int_id = int(channel_id)
            str_id = str(channel_id)
            return {
                "$or": [
                    {"_id": int_id},
                    {"_id": str_id},
                    {"chat_id": int_id},
                    {"channel_id": int_id},
                    {"chat_id": str_id},
                    {"channel_id": str_id},
                ]
            }
        except (ValueError, TypeError):
            return {
                "$or": [
                    {"_id": channel_id},
                    {"chat_id": channel_id},
                    {"channel_id": channel_id},
                ]
            }

    async def add_channel(self, channel_id: int, channel_name: str = "") -> bool:
        if await self.is_channel_exist(channel_id):
            return False
        global_timer = await self.get_global_req_timer()
        await self._channels.insert_one({
            "_id":        int(channel_id),
            "name":       channel_name,
            "added":      int(time.time()),
            "req_mode":   False,
            "req_timer":  global_timer,
            "link_count": 0,
        })
        return True

    async def remove_channel(self, channel_id) -> bool:
        result = await self._channels.delete_one(self._channel_filter(channel_id))
        return result.deleted_count > 0

    async def is_channel_exist(self, channel_id) -> bool:
        return bool(await self._channels.find_one(self._channel_filter(channel_id)))

    async def get_channel(self, channel_id) -> Optional[dict]:
        return await self._channels.find_one(self._channel_filter(channel_id))

    async def get_all_channels(self) -> list[dict]:
        return [doc async for doc in self._channels.find({"_id": {"$ne": _GLOBAL_TIMER_ID}})]

    async def total_channels(self) -> int:
        return await self._channels.count_documents({"_id": {"$ne": _GLOBAL_TIMER_ID}})

    async def update_channel_name(self, channel_id, name: str):
        await self._channels.update_one(
            self._channel_filter(channel_id),
            {"$set": {"name": name}},
            upsert=False,
        )

    # ── req_mode ──────────────────────────────────────────────────────────────

    async def set_req_mode(self, channel_id, enabled: bool):
        await self._channels.update_one(
            self._channel_filter(channel_id),
            {"$set": {"req_mode": enabled}}
        )

    async def get_req_mode(self, channel_id) -> bool:
        doc = await self._channels.find_one(self._channel_filter(channel_id), {"req_mode": 1})
        return doc.get("req_mode", False) if doc else False

    # ── req_timer ─────────────────────────────────────────────────────────────

    async def set_req_timer(self, channel_id, seconds: int):
        await self._channels.update_one(
            self._channel_filter(channel_id),
            {"$set": {"req_timer": seconds}}
        )

    async def get_req_timer(self, channel_id) -> int:
        doc = await self._channels.find_one(self._channel_filter(channel_id), {"req_timer": 1})
        return doc.get("req_timer", 0) if doc else 0

    async def set_global_req_timer(self, seconds: int):
        """Apply timer to ALL existing channels and store as global default."""
        await self._channels.update_many(
            {"_id": {"$ne": _GLOBAL_TIMER_ID}},
            {"$set": {"req_timer": seconds}}
        )
        await self._channels.update_one(
            {"_id": _GLOBAL_TIMER_ID},
            {"$set": {"req_timer": seconds}},
            upsert=True,
        )

    async def get_global_req_timer(self) -> int:
        doc = await self._channels.find_one({"_id": _GLOBAL_TIMER_ID})
        return doc.get("req_timer", 0) if doc else 0

    # ── Link count ────────────────────────────────────────────────────────────

    async def increment_link_count(self, channel_id):
        await self._channels.update_one(
            self._channel_filter(channel_id),
            {"$inc": {"link_count": 1}}
        )

    async def get_link_count(self, channel_id) -> int:
        doc = await self._channels.find_one(self._channel_filter(channel_id), {"link_count": 1})
        return doc.get("link_count", 0) if doc else 0

    async def reset_link_count(self, channel_id):
        await self._channels.update_one(
            self._channel_filter(channel_id),
            {"$set": {"link_count": 0}}
        )

    async def reset_all_link_counts(self):
        await self._channels.update_many(
            {"_id": {"$ne": _GLOBAL_TIMER_ID}},
            {"$set": {"link_count": 0}}
        )

    async def get_top_channels(self, limit: int = 10) -> list[dict]:
        cursor = self._channels.find(
            {"_id": {"$ne": _GLOBAL_TIMER_ID}},
            {"name": 1, "link_count": 1}
        ).sort("link_count", -1).limit(limit)
        return [doc async for doc in cursor]

    # ── Runtime Settings (editable via /config) ───────────────────────────────

    async def save_setting(self, key: str, value) -> None:
        """Upsert a single setting value."""
        await self._settings.update_one(
            {"_id": key},
            {"$set": {"value": value}},
            upsert=True,
        )

    async def get_setting(self, key: str):
        """Return a setting value, or None if not set."""
        doc = await self._settings.find_one({"_id": key})
        return doc["value"] if doc else None

    async def get_all_settings(self) -> dict:
        """Return all saved settings as a key→value dict."""
        return {doc["_id"]: doc["value"] async for doc in self._settings.find({})}

    async def delete_setting(self, key: str) -> None:
        await self._settings.delete_one({"_id": key})

    async def delete_all_settings(self) -> None:
        await self._settings.delete_many({})

    # ── Stats ─────────────────────────────────────────────────────────────────

    async def stats(self) -> dict:
        total_links = 0
        async for doc in self._channels.find(
            {"_id": {"$ne": _GLOBAL_TIMER_ID}}, {"link_count": 1}
        ):
            total_links += doc.get("link_count", 0)
        return {
            "users":       await self.total_users(),
            "channels":    await self.total_channels(),
            "total_links": total_links,
            "banned":      await self.total_banned(),
        }


CosmicBotz = _Database()

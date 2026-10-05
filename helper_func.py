import asyncio
import base64
import math
from datetime import datetime, timedelta, timezone
from typing import Optional, Union

from pyrogram import Client
from pyrogram.errors import (
    ChatAdminRequired,
    FloodWait,
    MessageDeleteForbidden,
    MessageIdInvalid,
    MessageNotModified,
    UserNotParticipant,
)
from pyrogram.types import ChatInviteLink, InlineKeyboardButton, Message

from config import FORCE_SUB_CHANNEL, LINK_EXPIRY_SECONDS, LOGGER

logger = LOGGER(__name__)

REQ_PREFIX = "req_"

# ── Bot username cache (set once at startup, never expires) ───────────────────
_BOT_USERNAME: str = ""

def set_bot_username(username: str) -> None:
    """Call this once from bot.py after super().start() to cache the username."""
    global _BOT_USERNAME
    _BOT_USERNAME = username
    logger.info("Bot username cached: @%s", username)

def get_bot_username() -> str:
    return _BOT_USERNAME


# ──────────────────────────────────────────────────────────────────────────────
#  Base64 helpers
# ──────────────────────────────────────────────────────────────────────────────

async def encode(string: str) -> str:
    b64 = base64.urlsafe_b64encode(string.encode("ascii"))
    return b64.decode("ascii").strip("=")


async def decode(b64_string: str) -> str:
    b64_string = b64_string.strip("=")
    padded = b64_string + "=" * (-len(b64_string) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii")).decode("ascii")


# ──────────────────────────────────────────────────────────────────────────────
#  Channel ID ↔ token
# ──────────────────────────────────────────────────────────────────────────────

async def encode_channel_id(channel_id: int) -> str:
    return await encode(str(channel_id))


async def encode_req_channel_id(channel_id: int) -> str:
    return f"{REQ_PREFIX}{await encode(str(channel_id))}"


async def decode_channel_token(token: str) -> tuple[Optional[int], bool]:
    """
    Decode any deep-link token → (channel_id, is_request_link).
    Returns (None, False) on failure.
    """
    try:
        is_req  = token.startswith(REQ_PREFIX)
        raw_b64 = token[len(REQ_PREFIX):] if is_req else token
        raw     = await decode(raw_b64)

        stripped = raw.strip()
        if stripped.lstrip("-").isdigit():
            return int(stripped), is_req

        if raw.startswith("channel_"):
            return int(raw.split("channel_", 1)[1]), is_req

    except Exception:
        pass

    return None, False


# ──────────────────────────────────────────────────────────────────────────────
#  Build deep-link URLs  — uses CACHED username, zero API calls
# ──────────────────────────────────────────────────────────────────────────────

async def build_links(client: Client, channel_id: int) -> tuple[str, str]:
    """
    Return (normal_deep_link, request_deep_link).

    Uses the cached bot username set at startup — no get_me() call,
    no FloodWait risk even in tight loops over many channels.

    Falls back to a live get_me() ONLY if cache is somehow empty
    (should never happen after bot.py sets it correctly).
    """
    username = _BOT_USERNAME
    if not username:
        # Safety fallback — only happens if set_bot_username() was not called
        logger.warning("Bot username cache empty — falling back to get_me(). "
                       "Ensure set_bot_username() is called in bot.py start().")
        me = await client.get_me()
        username = me.username

    normal_token = await encode_channel_id(channel_id)
    req_token    = await encode_req_channel_id(channel_id)
    return (
        f"https://t.me/{username}?start={normal_token}",
        f"https://t.me/{username}?start={req_token}",
    )


# ──────────────────────────────────────────────────────────────────────────────
#  Invite-link generation
# ──────────────────────────────────────────────────────────────────────────────

async def get_invite_link(client: Client, channel_id: int) -> Optional[str]:
    """
    Temp single-use invite link.
    Expires in LINK_EXPIRY_SECONDS. member_limit=1 auto-revokes after one use.
    """
    expire_at = datetime.now(timezone.utc) + timedelta(seconds=LINK_EXPIRY_SECONDS)
    try:
        link: ChatInviteLink = await client.create_chat_invite_link(
            chat_id=channel_id,
            expire_date=expire_at,
            member_limit=1,
        )
        return link.invite_link
    except ChatAdminRequired:
        logger.error("Bot lacks invite-link admin rights in channel %s.", channel_id)
    except FloodWait as e:
        logger.warning("FloodWait %ss — retrying invite link for %s.", e.value, channel_id)
        await asyncio.sleep(e.value + 1)
        return await get_invite_link(client, channel_id)
    except Exception as e:
        logger.exception("Error generating invite link for %s: %s", channel_id, e)
    return None


async def get_request_invite_link(client: Client, channel_id: int) -> Optional[str]:
    """
    Temp request-join link (creates_join_request=True).
    Expires in LINK_EXPIRY_SECONDS so it can't be scraped indefinitely.
    A new link is generated on every deep-link click — users always get a valid URL.
    """
    expire_at = datetime.now(timezone.utc) + timedelta(seconds=LINK_EXPIRY_SECONDS)
    try:
        link: ChatInviteLink = await client.create_chat_invite_link(
            chat_id=channel_id,
            expire_date=expire_at,
            creates_join_request=True,
        )
        return link.invite_link
    except ChatAdminRequired:
        logger.error("Bot lacks admin rights in channel %s for request link.", channel_id)
    except FloodWait as e:
        logger.warning("FloodWait %ss — retrying request link for %s.", e.value, channel_id)
        await asyncio.sleep(e.value + 1)
        return await get_request_invite_link(client, channel_id)
    except Exception as e:
        logger.exception("Error generating request link for %s: %s", channel_id, e)
    return None


# ──────────────────────────────────────────────────────────────────────────────
#  Force-subscription check
# ──────────────────────────────────────────────────────────────────────────────

async def is_subscribed(client: Client, user_id: int) -> bool:
    """True if FORCE_SUB_CHANNEL is disabled OR the user is an active member."""
    if not FORCE_SUB_CHANNEL:
        return True
    try:
        from pyrogram.enums import ChatMemberStatus
        member = await client.get_chat_member(FORCE_SUB_CHANNEL, user_id)
        return member.status not in (
            ChatMemberStatus.BANNED,
            ChatMemberStatus.LEFT,
        )
    except UserNotParticipant:
        return False
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
        return await is_subscribed(client, user_id)
    except Exception:
        return True  # fail-open


# ──────────────────────────────────────────────────────────────────────────────
#  Safe message helpers
# ──────────────────────────────────────────────────────────────────────────────

async def safe_delete(message: Message) -> None:
    try:
        await message.delete()
    except Exception:
        pass


async def safe_edit(message: Message, text: str, **kwargs) -> None:
    try:
        await message.edit_text(text, **kwargs)
    except MessageNotModified:
        pass
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
        await safe_edit(message, text, **kwargs)
    except Exception as e:
        logger.warning("safe_edit failed: %s", e)


# ──────────────────────────────────────────────────────────────────────────────
#  Pagination keyboard helper
# ──────────────────────────────────────────────────────────────────────────────

def paginate_keyboard(
    items: list[tuple[str, str]],
    page: int,
    per_page: int = 5,
    prefix: str = "page",
) -> tuple[list, int, int]:
    total       = len(items)
    total_pages = max(1, math.ceil(total / per_page))
    page        = max(0, min(page, total_pages - 1))

    chunk = items[page * per_page : page * per_page + per_page]
    rows  = [[InlineKeyboardButton(label, callback_data=cb)] for label, cb in chunk]

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("« ᴘʀᴇᴠ", callback_data=f"{prefix}:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("ɴᴇxᴛ »", callback_data=f"{prefix}:{page + 1}"))
    if nav:
        rows.append(nav)

    return rows, page, total_pages

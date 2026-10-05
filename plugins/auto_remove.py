"""
plugins/auto_remove.py
~~~~~~~~~~~~~~~~~~~~~~
PRO FEATURE — Safe auto-remove when bot is kicked/demoted from a channel.

Flow:
  1. Bot gets removed as admin (or kicked entirely) from a managed channel.
  2. Bot sends owner a DM with channel info and two buttons:
       [✅ ᴄᴏɴꜰɪʀᴍ ʀᴇᴍᴏᴠᴇ]  [❌ ᴋᴇᴇᴘ ɪᴛ]
  3. Owner taps Confirm  → channel is deleted from DB.
     Owner taps Keep     → nothing changes, message is updated.
  4. If owner doesn't respond within 10 minutes, nothing happens
     (no accidental removal ever).

This file is self-contained. Delete it to disable the feature without
touching anything else.
"""
import asyncio

from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import QueryIdInvalid
from pyrogram.types import (
    CallbackQuery,
    ChatMemberUpdated,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from config import LOGGER, OWNER_ID
from database import CosmicBotz
from helper_func import build_links   # kept for consistency (unused in this file)

logger = LOGGER(__name__)

# ── Pending confirmations: channel_id → message_id (to edit later) ───────────
# Stored in-memory. Resets on restart — safe because we never auto-delete.
_pending: dict[int, int] = {}


@Client.on_chat_member_updated()
async def on_bot_status_change(client: Client, update: ChatMemberUpdated):
    """
    Triggered when ANY member's status changes.
    We only care when the BOT itself is kicked/demoted from a managed channel.
    """
    new = update.new_chat_member
    old = update.old_chat_member
    chat = update.chat

    if new is None or old is None:
        return

    # This update must be about the bot itself
    me = await client.get_me()
    if new.user.id != me.id:
        return

    # Only care about channels the bot manages
    if not await CosmicBotz.is_channel_exist(chat.id):
        return

    was_admin = old.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    is_kicked = new.status in (ChatMemberStatus.BANNED, ChatMemberStatus.LEFT)
    is_member = new.status == ChatMemberStatus.MEMBER  # demoted to plain member

    # ── Bot was re-promoted to admin ─────────────────────────────────────
    if new.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
        ch_name = chat.title or str(chat.id)
        await CosmicBotz.update_channel_name(chat.id, ch_name)
        logger.info("Bot re-promoted in channel %s (%s).", chat.id, ch_name)

        # Cancel any pending removal confirmation
        if chat.id in _pending:
            _pending.pop(chat.id, None)
            try:
                await client.send_message(
                    OWNER_ID,
                    f"<blockquote>✅ ʙᴏᴛ ʀᴇsᴛᴏʀᴇᴅ ᴀs ᴀᴅᴍɪɴ ɪɴ <b>{ch_name}</b> — "
                    f"ʀᴇᴍᴏᴠᴀʟ ᴄᴀɴᴄᴇʟʟᴇᴅ.</blockquote>"
                )
            except Exception:
                pass
        return

    # ── Bot was kicked or demoted — ask owner ─────────────────────────────
    if not was_admin:
        return  # Was already not admin, nothing changed for us

    if not (is_kicked or is_member):
        return

    ch_name = chat.title or str(chat.id)
    ch_id   = chat.id
    reason  = "ᴋɪᴄᴋᴇᴅ / ʙᴀɴɴᴇᴅ" if is_kicked else "ᴅᴇᴍᴏᴛᴇᴅ ꜰʀᴏᴍ ᴀᴅᴍɪɴ"

    logger.warning("Bot %s from channel %s (%s). Asking owner.", reason, ch_id, ch_name)

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ ʀᴇᴍᴏᴠᴇ ꜰʀᴏᴍ ᴅʙ", callback_data=f"autoremove:confirm:{ch_id}"),
            InlineKeyboardButton("❌ ᴋᴇᴇᴘ ɪᴛ",         callback_data=f"autoremove:keep:{ch_id}"),
        ]
    ])

    try:
        msg = await client.send_message(
            OWNER_ID,
            f"<b>⚠️ ʙᴏᴛ ʀᴇᴍᴏᴠᴇᴅ ꜰʀᴏᴍ ᴄʜᴀɴɴᴇʟ</b>\n\n"
            f"<blockquote>"
            f"❍ ᴄʜᴀɴɴᴇʟ : <b>{ch_name}</b>\n"
            f"❍ ɪᴅ       : <code>{ch_id}</code>\n"
            f"❍ sᴛᴀᴛᴜs  : {reason}"
            f"</blockquote>\n\n"
            f"ᴅᴏ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ʀᴇᴍᴏᴠᴇ ɪᴛ ꜰʀᴏᴍ ᴛʜᴇ ᴅᴀᴛᴀʙᴀsᴇ?",
            reply_markup=keyboard,
        )
        _pending[ch_id] = msg.id

        # Auto-expire confirmation after 10 minutes
        asyncio.get_event_loop().call_later(
            600, lambda: _pending.pop(ch_id, None)
        )
    except Exception as e:
        logger.error("Could not DM owner about channel removal: %s", e)


@Client.on_callback_query(
    filters.regex(r"^autoremove:(confirm|keep):(-?\d+)$") & filters.user([OWNER_ID])
)
async def autoremove_callback(client: Client, cq: CallbackQuery):
    action     = cq.matches[0].group(1)
    channel_id = int(cq.matches[0].group(2))

    _pending.pop(channel_id, None)

    if action == "confirm":
        await CosmicBotz.remove_channel(channel_id)
        try:
            await cq.edit_message_text(
                f"<blockquote>🗑 ᴄʜᴀɴɴᴇʟ <code>{channel_id}</code> ʜᴀs ʙᴇᴇɴ ʀᴇᴍᴏᴠᴇᴅ ꜰʀᴏᴍ ᴛʜᴇ ᴅᴀᴛᴀʙᴀsᴇ.</blockquote>"
            )
        except (QueryIdInvalid, Exception):
            pass
        logger.info("Owner confirmed removal of channel %s.", channel_id)

    else:  # keep
        # Try to refresh the channel name if bot is still there
        ch_name = str(channel_id)
        try:
            chat    = await client.get_chat(channel_id)
            ch_name = chat.title or ch_name
            await CosmicBotz.update_channel_name(channel_id, ch_name)
        except Exception:
            pass

        try:
            await cq.edit_message_text(
                f"<blockquote>✅ ᴄʜᴀɴɴᴇʟ <b>{ch_name}</b> ᴋᴇᴘᴛ ɪɴ ᴅᴀᴛᴀʙᴀsᴇ.</blockquote>"
            )
        except (QueryIdInvalid, Exception):
            pass
        logger.info("Owner chose to keep channel %s in DB.", channel_id)

    try:
        await cq.answer()
    except QueryIdInvalid:
        pass
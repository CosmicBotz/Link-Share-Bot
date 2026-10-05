"""
plugins/start.py
~~~~~~~~~~~~~~~~
Handles /start, /help, /about.

Deep-link routing:
  ?start=<b64>       — normal flow  — temp single-use invite link
  ?start=req_<b64>   — request flow — temp request-join link

All user-visible text uses small caps Unicode style.
Blockquotes used for info sections.
"""
import asyncio
import random

from pyrogram import Client, filters
from pyrogram.errors import FloodWait, MessageNotModified, QueryIdInvalid
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import (
    ABOUT_TEXT,
    FORCE_SUB_CHANNEL,
    HELP_TEXT,
    LOGGER,
    OWNER_ID,
    START_PICS,
    START_TEXT,
)
from database import CosmicBotz
from helper_func import (
    decode_channel_token,
    get_bot_username,
    get_invite_link,
    get_request_invite_link,
    is_subscribed,
    safe_delete,
)
from rate_limit import check_rate_limit, RATE_LIMIT_MAX, RATE_LIMIT_WINDOW

logger = LOGGER(__name__)


# ──────────────────────────────────────────────────────────────────────────────
#  Default texts — small caps + blockquote style
# ──────────────────────────────────────────────────────────────────────────────

_DEFAULT_START = (
    "<b>ʜᴇʏ {mention}!</b>\n\n"
    "ɪ'ᴍ <b>ɴᴇxᴜs</b> — ʏᴏᴜʀ sᴇᴄᴜʀᴇ ᴄʜᴀɴɴᴇʟ ʟɪɴᴋ ᴍᴀɴᴀɢᴇʀ.\n\n"
    "ɪ ɢᴇɴᴇʀᴀᴛᴇ <b>ᴛᴇᴍᴘᴏʀᴀʀʏ, sɪɴɢʟᴇ-ᴜsᴇ ɪɴᴠɪᴛᴇ ʟɪɴᴋs</b> ꜰᴏʀ ᴘʀɪᴠᴀᴛᴇ "
    "ᴛᴇʟᴇɢʀᴀᴍ ᴄʜᴀɴɴᴇʟs sᴏ ᴛʜᴇ ʀᴇᴀʟ ɪɴᴠɪᴛᴇ ɪs ɴᴇᴠᴇʀ ʟᴇᴀᴋᴇᴅ ᴘᴜʙʟɪᴄʟʏ. "
    "ᴇᴠᴇʀʏ ᴄʟɪᴄᴋ ᴄʀᴇᴀᴛᴇs ᴀ ꜰʀᴇsʜ ʟɪɴᴋ ᴛʜᴀᴛ ᴇxᴘɪʀᴇs ɪɴ ᴍɪɴᴜᴛᴇs.\n\n"
    "<blockquote>"
    "❍ ᴅᴇᴠᴇʟᴏᴘᴇʀ : <a href='https://t.me/VoidxTora'>@VoidxTora</a>\n"
    "❍ ᴍᴀɪɴᴛᴀɪɴᴇᴅ ʙʏ : <a href='https://t.me/VoidxTora'>@VoidxTora</a>\n"
    "❍ ᴘʀᴏᴊᴇᴄᴛ : <a href='https://t.me/CosmicBotz'>@CosmicBotz</a>"
    "</blockquote>"
)

_DEFAULT_HELP = (
    "<b>ɴᴇxᴜs — ʜᴇʟᴘ</b>\n\n"
    "<blockquote>"
    "ᴛᴀᴘ ᴀɴʏ sʜᴀʀᴇ ʟɪɴᴋ ᴘᴏsᴛᴇᴅ ʙʏ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ — ɪ'ʟʟ ʜᴀɴᴅʟᴇ ᴛʜᴇ ʀᴇsᴛ.\n"
    "ɴᴏʀᴍᴀʟ ʟɪɴᴋ ɢɪᴠᴇs ᴀ ᴅɪʀᴇᴄᴛ ɪɴᴠɪᴛᴇ (5 ᴍɪɴ, sɪɴɢʟᴇ-ᴜsᴇ).\n"
    "ʀᴇǫᴜᴇsᴛ ʟɪɴᴋ sᴇɴᴅs ᴀ ᴊᴏɪɴ ʀᴇǫᴜᴇsᴛ ꜰᴏʀ ᴀᴅᴍɪɴ ᴀᴘᴘʀᴏᴠᴀʟ.\n"
    "ʟɪɴᴋ ᴇxᴘɪʀᴇᴅ? ᴛᴀᴘ ᴛʜᴇ ᴏʀɪɢɪɴᴀʟ ᴘᴏsᴛ ʟɪɴᴋ ᴀɢᴀɪɴ."
    "</blockquote>\n\n"
    "<b>❍ ᴀᴅᴍɪɴ ᴄᴏᴍᴍᴀɴᴅs</b>\n\n"
    "<blockquote>"
    "/addch — ʀᴇɢɪsᴛᴇʀ ᴀ ᴄʜᴀɴɴᴇʟ\n"
    "/delch — ʀᴇᴍᴏᴠᴇ ᴀ ᴄʜᴀɴɴᴇʟ\n"
    "/channels — ᴍᴀɴᴀɢᴇ ᴄʜᴀɴɴᴇʟs & ᴄᴏᴘʏ ʟɪɴᴋs\n"
    "/links — ᴀʟʟ ɴᴏʀᴍᴀʟ ᴅᴇᴇᴘ-ʟɪɴᴋs\n"
    "/reqlink — ᴀʟʟ ʀᴇǫᴜᴇsᴛ ᴅᴇᴇᴘ-ʟɪɴᴋs\n"
    "/bulklink — ʙᴏᴛʜ ʟɪɴᴋs ꜰᴏʀ ᴍᴜʟᴛɪᴘʟᴇ ᴄʜᴀɴɴᴇʟs\n"
    "/reqmode — ᴛᴏɢɢʟᴇ ᴀᴜᴛᴏ-ᴀᴘᴘʀᴏᴠᴇ ᴊᴏɪɴ ʀᴇǫᴜᴇsᴛs\n"
    "/reqtime — sᴇᴛ ᴀᴜᴛᴏ-ᴀᴘᴘʀᴏᴠᴇ ᴅᴇʟᴀʏ ɪɴ sᴇᴄᴏɴᴅs"
    "</blockquote>\n\n"
    "<b>❍ ᴏᴡɴᴇʀ ᴄᴏᴍᴍᴀɴᴅs</b>\n\n"
    "<blockquote>"
    "/broadcast — ᴍᴇssᴀɢᴇ ᴀʟʟ ᴜsᴇʀs\n"
    "/stats — ᴅʙ & ᴜᴘᴛɪᴍᴇ sᴛᴀᴛs\n"
    "/logs — ᴅᴏᴡɴʟᴏᴀᴅ ʟᴏɢ ꜰɪʟᴇ\n"
    "/cleanup — ʀᴇᴍᴏᴠᴇ ʙʟᴏᴄᴋᴇᴅ ᴜsᴇʀs"
    "</blockquote>\n\n"
    "<blockquote>"
    "❍ ᴍᴀɪɴᴛᴀɪɴᴇᴅ ʙʏ <a href='https://t.me/VoidxTora'>@VoidxTora</a> — "
    "<a href='https://t.me/CosmicBotz'>@CosmicBotz</a>"
    "</blockquote>"
)

_DEFAULT_ABOUT = (
    "<b>ɴᴇxᴜs ʟɪɴᴋ sʜᴀʀᴇ ʙᴏᴛ</b>\n\n"
    "<blockquote>"
    "❍ ʜᴏsᴛᴇᴅ ᴏɴ : ʀᴇɴᴅᴇʀ\n"
    "❍ ᴅᴀᴛᴀʙᴀsᴇ : ᴍᴏɴɢᴏ ᴅʙ\n"
    "❍ ʟᴀɴɢᴜᴀɢᴇ : ᴘʏᴛʜᴏɴ 3\n"
    "❍ ꜰʀᴀᴍᴇᴡᴏʀᴋ : ᴘʏʀᴏꜰᴏʀᴋ\n"
    "❍ ᴅᴇᴠᴇʟᴏᴘᴇʀ : <a href='https://t.me/VoidxTora'>@VoidxTora</a>\n"
    "❍ ᴍᴀɪɴᴛᴀɪɴᴇᴅ ʙʏ : <a href='https://t.me/VoidxTora'>@VoidxTora</a>\n"
    "❍ ᴘʀᴏᴊᴇᴄᴛ : <a href='https://t.me/CosmicBotz'>@CosmicBotz</a>"
    "</blockquote>\n\n"
    "<b>❍ ꜰᴇᴀᴛᴜʀᴇs</b>\n\n"
    "<blockquote>"
    "➻ ᴛᴇᴍᴘ sɪɴɢʟᴇ-ᴜsᴇ ɪɴᴠɪᴛᴇ ʟɪɴᴋs (ᴀᴜᴛᴏ-ᴇxᴘɪʀᴇ)\n"
    "➻ ᴛᴇᴍᴘ ʀᴇǫᴜᴇsᴛ-ᴊᴏɪɴ ʟɪɴᴋs (ᴀᴅᴍɪɴ ᴀᴘᴘʀᴏᴠᴇs)\n"
    "➻ ᴀᴜᴛᴏ-ᴀᴘᴘʀᴏᴠᴇ ᴊᴏɪɴ ʀᴇǫᴜᴇsᴛs ᴡɪᴛʜ ᴅᴇʟᴀʏ sᴜᴘᴘᴏʀᴛ\n"
    "➻ ꜰᴏʀᴄᴇ-sᴜʙsᴄʀɪʙᴇ ɢᴀᴛᴇ ʙᴇꜰᴏʀᴇ ʟɪɴᴋ ᴅᴇʟɪᴠᴇʀʏ\n"
    "➻ ᴘᴀɢɪɴᴀᴛᴇᴅ ᴄʜᴀɴɴᴇʟ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ ᴘᴀɴᴇʟ\n"
    "➻ ʙʀᴏᴀᴅᴄᴀsᴛ sʏsᴛᴇᴍ ᴡɪᴛʜ ʟɪᴠᴇ ᴘʀᴏɢʀᴇss\n"
    "➻ ᴍᴜʟᴛɪ-ᴘɪᴄ sᴛᴀʀᴛ sᴄʀᴇᴇɴ (ʀᴀɴᴅᴏᴍ ᴘɪᴄᴋ)\n"
    "➻ ɢʟᴏʙᴀʟ ᴇʀʀᴏʀ ʜᴀɴᴅʟᴇʀ — ʙᴏᴛ ɴᴇᴠᴇʀ ᴄʀᴀsʜᴇs\n"
    "➻ ᴄʟɪᴄᴋ ᴏɴ ᴛʜᴇ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ ꜰᴏʀ ᴍᴏʀᴇ ɪɴꜰᴏ."
    "</blockquote>"
)


# ──────────────────────────────────────────────────────────────────────────────
#  Text / pic resolvers
# ──────────────────────────────────────────────────────────────────────────────

def _start_text(mention: str) -> str:
    return (START_TEXT or _DEFAULT_START).replace("{mention}", mention)

def _help_text() -> str:
    return HELP_TEXT or _DEFAULT_HELP

def _about_text() -> str:
    return ABOUT_TEXT or _DEFAULT_ABOUT

def _pick_pic() -> str | None:
    return random.choice(START_PICS) if START_PICS else None


# ──────────────────────────────────────────────────────────────────────────────
#  Keyboards  (button labels in small caps)
# ──────────────────────────────────────────────────────────────────────────────

def _start_keyboard() -> InlineKeyboardMarkup:
    """Uses cached bot username — no API call."""
    username = get_bot_username()
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("❍ ᴏᴡɴᴇʀ",          url=f"tg://user?id={OWNER_ID}"),
            InlineKeyboardButton("➕ ᴀᴅᴅ ᴛᴏ ᴄʜᴀɴɴᴇʟ", url=f"https://t.me/{username}?startchannel=true"),
        ],
        [
            InlineKeyboardButton("❓ ʜᴇʟᴘ",  callback_data="cb_help"),
            InlineKeyboardButton("ℹ ᴀʙᴏᴜᴛ", callback_data="cb_about"),
        ],
    ])

def _back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("« ʙᴀᴄᴋ", callback_data="cb_start")]]
    )


# ──────────────────────────────────────────────────────────────────────────────
#  /start
# ──────────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("start") & filters.private & ~filters.forwarded)
async def start_handler(client: Client, message: Message):
    user = message.from_user
    if await CosmicBotz.is_user_banned(user.id):
        await message.reply_text(
            "<b>🚫 ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ</b>\n\n"
            "<blockquote>ʏᴏᴜ ʜᴀᴠᴇ ʙᴇᴇɴ ʙᴀɴɴᴇᴅ ꜰʀᴏᴍ ᴜsɪɴɢ ᴛʜɪs ʙᴏᴛ.</blockquote>"
        )
        return

    try:
        if await CosmicBotz.add_user(user.id):
            logger.info("ɴᴇᴡ ᴜsᴇʀ: %s (%s)", user.id, user.username)
    except Exception as e:
        logger.warning("DB add_user failed for %s: %s", user.id, e)

    args = message.command

    # ── Deep-link ─────────────────────────────────────────────────────────────
    if len(args) > 1:
        token = args[1]
        channel_id, is_req = await decode_channel_token(token)

        if channel_id is None:
            await message.reply_text(
                "<b>ɪɴᴠᴀʟɪᴅ ᴏʀ ᴇxᴘɪʀᴇᴅ ʟɪɴᴋ.</b>\n\n"
                "<blockquote>ᴘʟᴇᴀsᴇ ᴛᴀᴘ ᴛʜᴇ ᴏʀɪɢɪɴᴀʟ ᴘᴏsᴛ ʟɪɴᴋ ᴀɢᴀɪɴ ᴛᴏ ɢᴇᴛ ᴀ ꜰʀᴇsʜ ᴏɴᴇ.</blockquote>"
            )
            return

        # ── Rate limit check ──────────────────────────────────────────────────
        allowed, wait_secs = check_rate_limit(user.id)
        if not allowed:
            await message.reply_text(
                "<b>sʟᴏᴡ ᴅᴏᴡɴ!</b>\n\n"
                f"<blockquote>ʏᴏᴜ ᴄᴀɴ ʀᴇǫᴜᴇsᴛ ᴜᴘ ᴛᴏ <b>{RATE_LIMIT_MAX}</b> ʟɪɴᴋs "
                f"ᴇᴠᴇʀʏ <b>{RATE_LIMIT_WINDOW}s</b>.\n"
                f"ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ <b>{wait_secs}s</b> ʙᴇꜰᴏʀᴇ ᴛʀʏɪɴɢ ᴀɢᴀɪɴ.</blockquote>"
            )
            return

        # Force-sub gate
        if FORCE_SUB_CHANNEL and not await is_subscribed(client, user.id):
            kb = await _force_sub_keyboard(client, token)
            await message.reply_text(
                "<b>ʏᴏᴜ ɴᴇᴇᴅ ᴛᴏ ᴊᴏɪɴ ᴏᴜʀ ᴄʜᴀɴɴᴇʟ ꜰɪʀsᴛ.</b>\n\n"
                "<blockquote>ᴛᴀᴘ ᴛʜᴇ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ, ᴛʜᴇɴ ᴛᴀᴘ <b>ɪ'ᴠᴇ ᴊᴏɪɴᴇᴅ</b>.</blockquote>",
                reply_markup=kb,
            )
            return

        # Auto-register channel if bot is still admin there
        if not await CosmicBotz.is_channel_exist(channel_id):
            try:
                chat = await client.get_chat(channel_id)
                await CosmicBotz.add_channel(channel_id, chat.title or str(channel_id))
            except Exception:
                await message.reply_text(
                    "<b>ᴛʜɪs ᴄʜᴀɴɴᴇʟ ɪs ɴᴏ ʟᴏɴɢᴇʀ ᴀᴄᴄᴇssɪʙʟᴇ.</b>\n\n"
                    "<blockquote>ᴛʜᴇ ʙᴏᴛ ᴍᴀʏ ʜᴀᴠᴇ ʙᴇᴇɴ ʀᴇᴍᴏᴠᴇᴅ ᴏʀ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ ᴡᴀs ᴅᴇʟᴇᴛᴇᴅ.</blockquote>"
                )
                return

        channel_doc = await CosmicBotz.get_channel(channel_id)
        ch_name = (channel_doc or {}).get("name") or str(channel_id)

        # ── Request-join ──────────────────────────────────────────────────────
        if is_req:
            wait_msg = await message.reply_text("<i>ɢᴇɴᴇʀᴀᴛɪɴɢ ʏᴏᴜʀ ʟɪɴᴋ...</i>")
            req_url  = await get_request_invite_link(client, channel_id)
            await safe_delete(wait_msg)

            if not req_url:
                await message.reply_text(
                    "<b>ᴄᴏᴜʟᴅ ɴᴏᴛ ɢᴇɴᴇʀᴀᴛᴇ ᴀ ʟɪɴᴋ.</b>\n\n"
                    "<blockquote>ᴛʜᴇ ʙᴏᴛ ᴍᴀʏ ɴᴏᴛ ʜᴀᴠᴇ ɪɴᴠɪᴛᴇ-ʟɪɴᴋ ᴀᴅᴍɪɴ ʀɪɢʜᴛs ɪɴ ᴛʜɪs ᴄʜᴀɴɴᴇʟ.</blockquote>"
                )
                return

            # ── Increment link counter ────────────────────────────────────────
            await CosmicBotz.increment_link_count(channel_id)

            await message.reply_text(
                f"ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʟɪɴᴋ! ᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ᴛᴏ ᴘʀᴏᴄᴇᴇᴅ\n\n"
                f"<b>{ch_name}</b>\n\n"
                "<blockquote>ɴᴏᴛᴇ: ɪꜰ ᴛʜᴇ ʟɪɴᴋ ɪs ᴇxᴘɪʀᴇᴅ, ᴘʟᴇᴀsᴇ ᴛᴀᴘ ᴛʜᴇ ᴘᴏsᴛ ʟɪɴᴋ ᴀɢᴀɪɴ ᴛᴏ ɢᴇᴛ ᴀ ɴᴇᴡ ᴏɴᴇ.</blockquote>",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("➻ ʀᴇǫᴜᴇsᴛ ᴛᴏ ᴊᴏɪɴ", url=req_url)
                ]]),
                disable_web_page_preview=True,
            )
            return

        # ── Normal invite ─────────────────────────────────────────────────────
        wait_msg   = await message.reply_text("<i>ɢᴇɴᴇʀᴀᴛɪɴɢ ʏᴏᴜʀ ʟɪɴᴋ...</i>")
        invite_url = await get_invite_link(client, channel_id)
        await safe_delete(wait_msg)

        if not invite_url:
            await message.reply_text(
                "<b>ᴄᴏᴜʟᴅ ɴᴏᴛ ɢᴇɴᴇʀᴀᴛᴇ ᴀɴ ɪɴᴠɪᴛᴇ ʟɪɴᴋ.</b>\n\n"
                "<blockquote>ᴛʜᴇ ʙᴏᴛ ᴍᴀʏ ɴᴏᴛ ʜᴀᴠᴇ ᴀᴅᴍɪɴ ʀɪɢʜᴛs. ᴛᴀᴘ ᴛʜᴇ ᴏʀɪɢɪɴᴀʟ ᴘᴏsᴛ ʟɪɴᴋ ᴛᴏ ʀᴇᴛʀʏ.</blockquote>"
            )
            return

        # ── Increment link counter ────────────────────────────────────────────
        await CosmicBotz.increment_link_count(channel_id)

        await message.reply_text(
            f"ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʟɪɴᴋ! ᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ᴛᴏ ᴘʀᴏᴄᴇᴇᴅ\n\n"
            f"<b>{ch_name}</b>\n\n"
            "<blockquote>ᴛʜɪs ʟɪɴᴋ ᴇxᴘɪʀᴇs ɪɴ 5 ᴍɪɴᴜᴛᴇs ᴀɴᴅ ɪs sɪɴɢʟᴇ-ᴜsᴇ.\n"
            "ɴᴏᴛᴇ: ɪꜰ ᴛʜᴇ ʟɪɴᴋ ɪs ᴇxᴘɪʀᴇᴅ, ᴘʟᴇᴀsᴇ ᴛᴀᴘ ᴛʜᴇ ᴘᴏsᴛ ʟɪɴᴋ ᴀɢᴀɪɴ ᴛᴏ ɢᴇᴛ ᴀ ɴᴇᴡ ᴏɴᴇ.</blockquote>",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("➻ ᴊᴏɪɴ ɴᴏᴡ", url=invite_url)
            ]]),
            disable_web_page_preview=True,
        )
        return

    # ── Plain /start ──────────────────────────────────────────────────────────
    text     = _start_text(user.mention)
    pic      = _pick_pic()
    keyboard = _start_keyboard()

    if pic:
        pic_lower = pic.lower()
        if pic_lower.endswith((".gif", ".mp4")):
            try:
                await message.reply_animation(animation=pic, caption=text, reply_markup=keyboard)
                return
            except Exception as e:
                logger.warning("Start animation failed (url=%s): %s — trying photo fallback.", pic, e)
        try:
            await message.reply_photo(photo=pic, caption=text, reply_markup=keyboard)
            return
        except Exception as e:
            logger.warning("Start photo failed (url=%s): %s — trying animation fallback.", pic, e)
            try:
                await message.reply_animation(animation=pic, caption=text, reply_markup=keyboard)
                return
            except Exception as e2:
                logger.warning("Start animation fallback also failed: %s — using text.", e2)

    await message.reply_text(text, reply_markup=keyboard, disable_web_page_preview=True)


# ──────────────────────────────────────────────────────────────────────────────
#  /help
# ──────────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("help") & filters.private)
async def help_handler(client: Client, message: Message):
    await message.reply_text(_help_text(), disable_web_page_preview=True)


@Client.on_callback_query(filters.regex(r"^cb_help$"))
async def help_callback(client: Client, cq: CallbackQuery):
    try:
        await cq.edit_message_text(
            _help_text(), reply_markup=_back_keyboard(), disable_web_page_preview=True
        )
    except (MessageNotModified, QueryIdInvalid):
        pass
    await _safe_answer(cq)


# ──────────────────────────────────────────────────────────────────────────────
#  /about
# ──────────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("about") & filters.private)
async def about_handler(client: Client, message: Message):
    await message.reply_text(_about_text(), disable_web_page_preview=True)


@Client.on_callback_query(filters.regex(r"^cb_about$"))
async def about_callback(client: Client, cq: CallbackQuery):
    try:
        await cq.edit_message_text(
            _about_text(), reply_markup=_back_keyboard(), disable_web_page_preview=True
        )
    except (MessageNotModified, QueryIdInvalid):
        pass
    await _safe_answer(cq)


# ──────────────────────────────────────────────────────────────────────────────
#  Back to start
# ──────────────────────────────────────────────────────────────────────────────

@Client.on_callback_query(filters.regex(r"^cb_start$"))
async def back_to_start_callback(client: Client, cq: CallbackQuery):
    text     = _start_text(cq.from_user.mention)
    keyboard = _start_keyboard()
    try:
        await cq.edit_message_text(
            text, reply_markup=keyboard, disable_web_page_preview=True
        )
    except (MessageNotModified, QueryIdInvalid):
        pass
    await _safe_answer(cq)


# ──────────────────────────────────────────────────────────────────────────────
#  Force-sub keyboard
# ──────────────────────────────────────────────────────────────────────────────

async def _force_sub_keyboard(client: Client, deep_token: str) -> InlineKeyboardMarkup:
    try:
        chat = await client.get_chat(FORCE_SUB_CHANNEL)
        link = chat.invite_link or (
            await client.create_chat_invite_link(FORCE_SUB_CHANNEL)
        ).invite_link
    except Exception:
        link = "https://t.me"

    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ", url=link)],
        [InlineKeyboardButton("✓ ɪ'ᴠᴇ ᴊᴏɪɴᴇᴅ",  callback_data=f"check_sub:{deep_token}")],
    ])


# ──────────────────────────────────────────────────────────────────────────────
#  Force-sub verify callback
# ──────────────────────────────────────────────────────────────────────────────

@Client.on_callback_query(filters.regex(r"^check_sub:(.+)$"))
async def check_sub_callback(client: Client, cq: CallbackQuery):
    user  = cq.from_user
    token = cq.matches[0].group(1)

    if await CosmicBotz.is_user_banned(user.id):
        await _safe_answer(cq, "ʏᴏᴜ ᴀʀᴇ ʙᴀɴɴᴇᴅ ꜰʀᴏᴍ ᴜsɪɴɢ ᴛʜɪs ʙᴏᴛ.", alert=True)
        return

    if not await is_subscribed(client, user.id):
        await _safe_answer(cq, "ʏᴏᴜ ʜᴀᴠᴇɴ'ᴛ ᴊᴏɪɴᴇᴅ ʏᴇᴛ. ᴘʟᴇᴀsᴇ ᴊᴏɪɴ ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ.", alert=True)
        return

    await _safe_answer(cq, "✓ ᴠᴇʀɪꜰɪᴇᴅ!")
    await safe_delete(cq.message)

    channel_id, is_req = await decode_channel_token(token)
    if channel_id is None:
        await client.send_message(user.id, "<b>ɪɴᴠᴀʟɪᴅ ᴏʀ ᴇxᴘɪʀᴇᴅ ʟɪɴᴋ.</b>")
        return

    if not await CosmicBotz.is_channel_exist(channel_id):
        await client.send_message(user.id, "<b>ᴄʜᴀɴɴᴇʟ ɪs ɴᴏ ʟᴏɴɢᴇʀ ʀᴇɢɪsᴛᴇʀᴇᴅ.</b>")
        return

    channel_doc = await CosmicBotz.get_channel(channel_id)
    ch_name = (channel_doc or {}).get("name") or str(channel_id)

    if is_req:
        req_url = await get_request_invite_link(client, channel_id)
        if not req_url:
            await client.send_message(
                user.id,
                "<b>ᴄᴏᴜʟᴅ ɴᴏᴛ ɢᴇɴᴇʀᴀᴛᴇ ᴀ ʟɪɴᴋ.</b>\n\n"
                "<blockquote>ʙᴏᴛ ᴍᴀʏ ʟᴀᴄᴋ ᴀᴅᴍɪɴ ʀɪɢʜᴛs.</blockquote>"
            )
            return
        await client.send_message(
            user.id,
            f"ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʟɪɴᴋ! ᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ᴛᴏ ᴘʀᴏᴄᴇᴇᴅ\n\n"
            f"<b>{ch_name}</b>\n\n"
            "<blockquote>ɴᴏᴛᴇ: ɪꜰ ᴛʜᴇ ʟɪɴᴋ ɪs ᴇxᴘɪʀᴇᴅ, ᴛᴀᴘ ᴛʜᴇ ᴏʀɪɢɪɴᴀʟ ᴘᴏsᴛ ʟɪɴᴋ ᴛᴏ ɢᴇᴛ ᴀ ɴᴇᴡ ᴏɴᴇ.</blockquote>",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("➻ ʀᴇǫᴜᴇsᴛ ᴛᴏ ᴊᴏɪɴ", url=req_url)
            ]]),
        )
        return

    invite_url = await get_invite_link(client, channel_id)
    if not invite_url:
        await client.send_message(
            user.id,
            "<b>ᴄᴏᴜʟᴅ ɴᴏᴛ ɢᴇɴᴇʀᴀᴛᴇ ᴀɴ ɪɴᴠɪᴛᴇ ʟɪɴᴋ.</b>\n\n"
            "<blockquote>ʙᴏᴛ ᴍᴀʏ ʟᴀᴄᴋ ᴀᴅᴍɪɴ ʀɪɢʜᴛs.</blockquote>"
        )
        return

    await client.send_message(
        user.id,
        f"ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʟɪɴᴋ! ᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ᴛᴏ ᴘʀᴏᴄᴇᴇᴅ\n\n"
        f"<b>{ch_name}</b>\n\n"
        "<blockquote>ᴛʜɪs ʟɪɴᴋ ᴇxᴘɪʀᴇs ɪɴ 5 ᴍɪɴᴜᴛᴇs ᴀɴᴅ ɪs sɪɴɢʟᴇ-ᴜsᴇ.\n"
        "ɴᴏᴛᴇ: ɪꜰ ᴛʜᴇ ʟɪɴᴋ ɪs ᴇxᴘɪʀᴇᴅ, ᴛᴀᴘ ᴛʜᴇ ᴏʀɪɢɪɴᴀʟ ᴘᴏsᴛ ʟɪɴᴋ ᴛᴏ ɢᴇᴛ ᴀ ɴᴇᴡ ᴏɴᴇ.</blockquote>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("➻ ᴊᴏɪɴ ɴᴏᴡ", url=invite_url)
        ]]),
    )


# ──────────────────────────────────────────────────────────────────────────────
#  Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

async def _safe_answer(cq: CallbackQuery, text: str = "", alert: bool = False) -> None:
    try:
        await cq.answer(text, show_alert=alert)
    except (QueryIdInvalid, Exception):
        pass

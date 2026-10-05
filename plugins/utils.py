"""
plugins/utils.py
~~~~~~~~~~~~~~~~
Utility commands.

Public (anyone):
  /ping   — ʙᴏᴛ ʟᴀᴛᴇɴᴄʏ
  /id     — ɢᴇᴛ ɪᴅ ᴏꜰ ᴀɴʏ ᴜsᴇʀ, ᴄʜᴀᴛ ᴏʀ sᴇʟꜰ
             • ɴᴏ ʀᴇᴘʟʏ / ɴᴏ ᴀʀɢs → ʏᴏᴜʀ ᴏᴡɴ ɪᴅ
             • ʀᴇᴘʟʏ ᴛᴏ ᴜsᴇʀ     → ᴛʜᴀᴛ ᴜsᴇʀ's ɪᴅ
             • ꜰᴏʀᴡᴀʀᴅ           → ᴏʀɪɢɪɴᴀʟ sᴇɴᴅᴇʀ's ɪᴅ
             • ᴄʜᴀɴɴᴇʟ ᴍsɢ       → ᴄʜᴀɴɴᴇʟ ɪᴅ + ɴᴀᴍᴇ
             • /id @username      → ᴛʜᴀᴛ ᴜsᴇʀ's ᴏʀ ᴄʜᴀᴛ's ɪᴅ

Admin:
  /top     — ᴛᴏᴘ ᴄʜᴀɴɴᴇʟs ʙʏ ʟɪɴᴋ ᴄᴏᴜɴᴛ
  /checkch — ᴄʜᴀɴɴᴇʟ ʜᴇᴀʟᴛʜ ᴄʜᴇᴄᴋ
"""
import time

from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus, ChatType
from pyrogram.errors import (
    ChatAdminRequired,
    PeerIdInvalid,
    UsernameInvalid,
    UsernameNotOccupied,
    UserNotParticipant,
)
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import ADMINS, LOGGER
from database import CosmicBotz

logger = LOGGER(__name__)
admin_filter = filters.user(ADMINS)


# ──────────────────────────────────────────────────────────────────────────────
#  /ping
# ──────────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("ping") & filters.private)
async def ping_handler(client: Client, message: Message):
    start   = time.monotonic()
    sent    = await message.reply_text("<i>ᴘɪɴɢɪɴɢ...</i>")
    latency = (time.monotonic() - start) * 1000
    await sent.edit_text(
        f"<blockquote>🏓 ᴘᴏɴɢ!\n❍ ʟᴀᴛᴇɴᴄʏ : <b>{latency:.0f}ms</b></blockquote>"
    )


# ──────────────────────────────────────────────────────────────────────────────
#  /id — multi-mode: self / replied user / forwarded origin / channel / @username
# ──────────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("id") & filters.private)
async def id_handler(client: Client, message: Message):
    args  = message.command[1:]   # e.g. ["@VoidxTora"] or []
    reply = message.reply_to_message

    # ── Mode 1: /id @username or /id <user_id> or /id <link> ─────────────────
    if args:
        raw = args[0].strip()
        clean = raw
        if "t.me/" in clean:
            clean = clean.split("t.me/")[-1].split("?")[0].strip("/")

        # Step 1: Try Pyrogram get_users
        try:
            target_query = int(clean) if clean.lstrip("-").isdigit() else clean
            target = await client.get_users(target_query)
            uname  = f"@{target.username}" if target.username else "ɴᴏɴᴇ"
            dc_str = f"\n❍ ᴅᴄ ɪᴅ     : {target.dc_id}" if getattr(target, "dc_id", None) else ""
            await message.reply_text(
                "<b>👤 ᴜsᴇʀ ɪɴꜰᴏ</b>\n\n"
                "<blockquote>"
                f"❍ ɴᴀᴍᴇ     : {target.mention}\n"
                f"❍ ᴜsᴇʀɴᴀᴍᴇ : {uname}\n"
                f"❍ ɪᴅ       : <code>{target.id}</code>\n"
                f"❍ ʙᴏᴛ      : {'ʏᴇs' if target.is_bot else 'ɴᴏ'}"
                f"{dc_str}"
                "</blockquote>"
            )
            return
        except Exception:
            pass

        # Step 2: Try Pyrogram get_chat (handles channels, groups, invite links)
        for cand in (clean, raw):
            try:
                chat_query = int(cand) if cand.lstrip("-").isdigit() else cand
                chat = await client.get_chat(chat_query)
                await _send_chat_id(message, chat)
                return
            except Exception:
                pass

        await message.reply_text(
            f"<blockquote>❌ ᴄᴏᴜʟᴅ ɴᴏᴛ ꜰɪɴᴅ ᴏʀ ʀᴇsᴏʟᴠᴇ: <code>{raw}</code></blockquote>"
        )
        return

    # ── Mode 2: reply to a message ────────────────────────────────────────────
    if reply:
        # 2a: Forwarded from a channel → show channel info
        if reply.forward_from_chat and reply.forward_from_chat.type == ChatType.CHANNEL:
            await _send_chat_id(message, reply.forward_from_chat)
            return

        # 2b: Forwarded from a hidden user
        if reply.forward_sender_name and not reply.forward_from:
            await message.reply_text(
                "<blockquote>"
                "❍ ɴᴀᴍᴇ : <b>" + reply.forward_sender_name + "</b>\n"
                "❍ ɪᴅ   : ʜɪᴅᴅᴇɴ (ᴘʀɪᴠᴀᴄʏ ᴇɴᴀʙʟᴇᴅ)"
                "</blockquote>"
            )
            return

        # 2c: Forwarded from a normal user
        if reply.forward_from:
            u     = reply.forward_from
            uname = f"@{u.username}" if u.username else "ɴᴏɴᴇ"
            dc_str = f"\n❍ ᴅᴄ ɪᴅ     : {u.dc_id}" if getattr(u, "dc_id", None) else ""
            await message.reply_text(
                "<b>👤 ꜰᴏʀᴡᴀʀᴅᴇᴅ ꜰʀᴏᴍ</b>\n\n"
                "<blockquote>"
                f"❍ ɴᴀᴍᴇ     : {u.mention}\n"
                f"❍ ᴜsᴇʀɴᴀᴍᴇ : {uname}\n"
                f"❍ ɪᴅ       : <code>{u.id}</code>\n"
                f"❍ ʙᴏᴛ      : {'ʏᴇs' if u.is_bot else 'ɴᴏ'}"
                f"{dc_str}"
                "</blockquote>"
            )
            return

        # 2d: Replied-to sender_chat (channel post / anonymous group admin)
        if reply.sender_chat:
            await _send_chat_id(message, reply.sender_chat)
            return

        # 2e: Replied-to user
        if reply.from_user:
            u     = reply.from_user
            uname = f"@{u.username}" if u.username else "ɴᴏɴᴇ"
            dc_str = f"\n❍ ᴅᴄ ɪᴅ     : {u.dc_id}" if getattr(u, "dc_id", None) else ""
            await message.reply_text(
                "<b>👤 ᴜsᴇʀ ɪɴꜰᴏ</b>\n\n"
                "<blockquote>"
                f"❍ ɴᴀᴍᴇ     : {u.mention}\n"
                f"❍ ᴜsᴇʀɴᴀᴍᴇ : {uname}\n"
                f"❍ ɪᴅ       : <code>{u.id}</code>\n"
                f"❍ ʙᴏᴛ      : {'ʏᴇs' if u.is_bot else 'ɴᴏ'}"
                f"{dc_str}"
                "</blockquote>"
            )
            return

        # 2f: If replied message contains text with username or channel link, resolve it
        text_content = reply.text or reply.caption or ""
        words = text_content.split()
        for w in words:
            if w.startswith("@") or "t.me/" in w:
                clean_w = w.split("t.me/")[-1].split("?")[0].strip("/") if "t.me/" in w else w
                try:
                    chat = await client.get_chat(int(clean_w) if clean_w.lstrip("-").isdigit() else clean_w)
                    await _send_chat_id(message, chat)
                    return
                except Exception:
                    pass
                try:
                    u = await client.get_users(clean_w)
                    uname = f"@{u.username}" if u.username else "ɴᴏɴᴇ"
                    dc_str = f"\n❍ ᴅᴄ ɪᴅ     : {u.dc_id}" if getattr(u, "dc_id", None) else ""
                    await message.reply_text(
                        "<b>👤 ᴜsᴇʀ ɪɴꜰᴏ</b>\n\n"
                        "<blockquote>"
                        f"❍ ɴᴀᴍᴇ     : {u.mention}\n"
                        f"❍ ᴜsᴇʀɴᴀᴍᴇ : {uname}\n"
                        f"❍ ɪᴅ       : <code>{u.id}</code>\n"
                        f"❍ ʙᴏᴛ      : {'ʏᴇs' if u.is_bot else 'ɴᴏ'}"
                        f"{dc_str}"
                        "</blockquote>"
                    )
                    return
                except Exception:
                    pass

    # ── Mode 3: no args, no reply → self ─────────────────────────────────────
    u     = message.from_user
    uname = f"@{u.username}" if u.username else "ɴᴏɴᴇ"
    dc_str = f"\n❍ ᴅᴄ ɪᴅ     : {u.dc_id}" if getattr(u, "dc_id", None) else ""
    await message.reply_text(
        "<b>👤 ʏᴏᴜʀ ɪɴꜰᴏ</b>\n\n"
        "<blockquote>"
        f"❍ ɴᴀᴍᴇ     : {u.mention}\n"
        f"❍ ᴜsᴇʀɴᴀᴍᴇ : {uname}\n"
        f"❍ ɪᴅ       : <code>{u.id}</code>"
        f"{dc_str}"
        "</blockquote>"
    )


async def _send_chat_id(message: Message, chat) -> None:
    """Send formatted channel/group info block."""
    uname = f"@{chat.username}" if getattr(chat, "username", None) else "ᴘʀɪᴠᴀᴛᴇ"
    ctype = str(getattr(chat, "type", "")).replace("ChatType.", "").lower()
    dc_str = f"\n❍ ᴅᴄ ɪᴅ     : {chat.dc_id}" if getattr(chat, "dc_id", None) else ""
    await message.reply_text(
        "<b>📢 ᴄʜᴀᴛ ɪɴꜰᴏ</b>\n\n"
        "<blockquote>"
        f"❍ ɴᴀᴍᴇ     : <b>{chat.title}</b>\n"
        f"❍ ᴜsᴇʀɴᴀᴍᴇ : {uname}\n"
        f"❍ ɪᴅ       : <code>{chat.id}</code>\n"
        f"❍ ᴛʏᴘᴇ     : {ctype}"
        f"{dc_str}"
        "</blockquote>"
    )


# ──────────────────────────────────────────────────────────────────────────────
#  /top  — admins
# ──────────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("top") & filters.private & admin_filter)
async def top_handler(client: Client, message: Message):
    channels = await CosmicBotz.get_top_channels(limit=10)
    if not channels:
        await message.reply_text(
            "<blockquote>📭 ɴᴏ ʟɪɴᴋs ɢᴇɴᴇʀᴀᴛᴇᴅ ʏᴇᴛ.</blockquote>"
        )
        return

    medals = ["🥇", "🥈", "🥉"] + ["❍"] * 7
    lines  = ["<b>📊 ᴛᴏᴘ ᴄʜᴀɴɴᴇʟs ʙʏ ʟɪɴᴋ ᴄᴏᴜɴᴛ</b>\n"]
    for i, ch in enumerate(channels):
        name  = (ch.get("name") or "").strip() or f"Channel {ch['_id']}"
        count = ch.get("link_count", 0)
        lines.append(f"{medals[i]} <b>{name}</b>  —  <code>{count}</code> ʟɪɴᴋs")

    await message.reply_text("\n".join(lines))


# ──────────────────────────────────────────────────────────────────────────────
#  /checkch  — admins
# ──────────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("checkch") & filters.private & admin_filter)
async def checkch_handler(client: Client, message: Message):
    channels = await CosmicBotz.get_all_channels()
    if not channels:
        await message.reply_text("<blockquote>📭 ɴᴏ ᴄʜᴀɴɴᴇʟs ʀᴇɢɪsᴛᴇʀᴇᴅ.</blockquote>")
        return

    wait = await message.reply_text(
        f"<blockquote>🔍 ᴄʜᴇᴄᴋɪɴɢ <b>{len(channels)}</b> ᴄʜᴀɴɴᴇʟs…</blockquote>"
    )
    ok_list: list[str] = []
    broken:  list[str] = []

    for ch in channels:
        ch_id   = ch["_id"]
        ch_name = (ch.get("name") or "").strip() or f"Channel {ch_id}"
        try:
            me = await client.get_chat_member(ch_id, "me")
            if me.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
                ok_list.append(f"✅ <b>{ch_name}</b>  <code>{ch_id}</code>")
            else:
                broken.append(f"⚠️ <b>{ch_name}</b>  <code>{ch_id}</code>  (ᴅᴇᴍᴏᴛᴇᴅ)")
        except (ChatAdminRequired, UserNotParticipant, Exception):
            broken.append(f"❌ <b>{ch_name}</b>  <code>{ch_id}</code>  (ɴᴏ ᴀᴄᴄᴇss)")

    await wait.delete()
    parts = [f"<b>🔍 ᴄʜᴀɴɴᴇʟ ʜᴇᴀʟᴛʜ ᴄʜᴇᴄᴋ</b>  [{len(channels)} ᴛᴏᴛᴀʟ]\n"]
    if ok_list:
        parts.append("<b>ᴡᴏʀᴋɪɴɢ:</b>")
        parts.extend(ok_list)
    if broken:
        parts.append("\n<b>ɪssᴜᴇs:</b>")
        parts.extend(broken)
        parts.append(
            "\n<blockquote>ᴜsᴇ /delch &lt;ɪᴅ&gt; ᴏʀ ʀᴇ-ᴀᴅᴅ ʙᴏᴛ ᴀs ᴀᴅᴍɪɴ.</blockquote>"
        )
    else:
        parts.append("\n<blockquote>✅ ᴀʟʟ ᴄʜᴀɴɴᴇʟs ʜᴇᴀʟᴛʜʏ!</blockquote>")

    await message.reply_text("\n".join(parts))

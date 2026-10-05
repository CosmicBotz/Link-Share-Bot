import asyncio
import json
import os
import random
import shutil
import sys
from datetime import datetime

import aiohttp
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, InputUserDeactivated, UserIsBlocked
from pyrogram.types import Message

import config
from config import ADMINS, DEPLOY_HOOK_URL, LOG_FILE_NAME, LOGGER, OWNER_ID, send_log
from database import CosmicBotz

logger = LOGGER(__name__)

admin_filter = filters.user(ADMINS)
owner_filter = filters.user([OWNER_ID])

RESTART_STATE_FILE = "restart.json"

# ── Roasts ────────────────────────────────────────────────────────────────────
_ROASTS = [
    "ʙʀᴏ ʀᴇᴀʟʟʏ ᴛʜᴏᴜɢʜᴛ ʜᴇ ᴡᴀs ᴀɴ ᴀᴅᴍɪɴ. 💀",
    "ᴛʜᴇ ᴀᴜᴅᴀᴄɪᴛʏ. ɢᴇɴᴜɪɴᴇʟʏ ɪᴍᴘʀᴇssɪᴠᴇ.",
    "ʙᴏʟᴅ ᴍᴏᴠᴇ. ᴜɴꜰᴏʀᴛᴜɴᴀᴛᴇʟʏ, ɴᴏ.",
    "sɪʀ ᴛʜɪs ɪs ᴀ ᴛᴇʟᴇɢʀᴀᴍ ʙᴏᴛ, ɴᴏᴛ ᴀ ᴅᴇᴍᴏᴄʀᴀᴄʏ.",
    "ɴɪᴄᴇ ᴛʀʏ. ᴀᴅᴍɪɴ ᴘʀɪᴠɪʟᴇɢᴇs ɴᴏᴛ ɪɴᴄʟᴜᴅᴇᴅ ᴡɪᴛʜ ʏᴏᴜʀ ꜰʀᴇᴇ ᴀᴄᴄᴏᴜɴᴛ.",
    "ʏᴏᴜ'ʀᴇ ʟɪᴋᴇ 6 ᴘᴇʀᴍɪssɪᴏɴ ʟᴇᴠᴇʟs sʜᴏʀᴛ ᴏꜰ ᴜsɪɴɢ ᴛʜᴀᴛ ᴄᴏᴍᴍᴀɴᴅ.",
    "ɪ'ᴅ sᴀʏ ᴛʀʏ ᴀɢᴀɪɴ, ʙᴜᴛ ɪᴛ ᴡᴏɴ'ᴛ ʜᴇʟᴘ.",
    "ɴᴏᴛ ʏᴏᴜ. ɴᴇᴠᴇʀ ʏᴏᴜ.",
    "ᴛʜᴀᴛ ᴄᴏᴍᴍᴀɴᴅ ɪs ᴀʙᴏᴠᴇ ʏᴏᴜʀ ᴘᴀʏ ɢʀᴀᴅᴇ. ᴀᴄᴛᴜᴀʟʟʏ, ᴀɴʏ ᴘᴀʏ ɢʀᴀᴅᴇ.",
    "ɪᴍᴀɢɪɴᴇ ʜᴀᴠɪɴɢ ᴀᴅᴍɪɴ ᴀᴄᴄᴇss. ᴍᴜsᴛ ʙᴇ ɴɪᴄᴇ.",
    "ᴛʜᴇ ᴀɴsᴡᴇʀ ɪs ɴᴏ. ᴛʜᴇ ᴀɴsᴡᴇʀ ᴡɪʟʟ ᴀʟᴡᴀʏs ʙᴇ ɴᴏ.",
    "ᴇʀʀᴏʀ 403: ʏᴏᴜ'ʀᴇ ɴᴏᴛ ᴛʜᴀᴛ ɢᴜʏ.",
    "ᴡʜᴏ ᴛᴏʟᴅ ʏᴏᴜ ᴛʜᴀᴛ ᴡᴏᴜʟᴅ ᴡᴏʀᴋ? ꜰɪʀᴇ ᴛʜᴇᴍ.",
    "ɪ'ᴠᴇ sᴇᴇɴ ʙᴏᴛs ᴡɪᴛʜ ᴍᴏʀᴇ ᴀᴅᴍɪɴ ʀɪɢʜᴛs ᴛʜᴀɴ ʏᴏᴜ.",
    "ᴏɴᴇ ᴅᴀʏ ʏᴏᴜ'ʟʟ ꜰɪɴᴅ ᴀ ᴄᴏᴍᴍᴀɴᴅ ʏᴏᴜ ᴄᴀɴ ᴜsᴇ. ᴛᴏᴅᴀʏ ɪs ɴᴏᴛ ᴛʜᴀᴛ ᴅᴀʏ.",
    "ᴀʜ ʏᴇs, ᴛʜᴇ ᴄʟᴀssɪᴄ 'ʟᴇᴛ ᴍᴇ ᴊᴜsᴛ ᴛʀʏ ᴀɴᴅ sᴇᴇ' ᴍᴏᴠᴇ.",
    "ʏᴏᴜʀ ᴘᴇʀᴍɪssɪᴏɴ ʟᴇᴠᴇʟ: 🚫  ʀᴇǫᴜɪʀᴇᴅ: ᴀᴅᴍɪɴ.",
]

def _roast() -> str:
    return random.choice(_ROASTS)


_ADMIN_CMDS = [
    "stats", "status", "users", "broadcast", "cleanup", "logs",
    "addch", "delch", "channels", "links", "reqlink", "bulklink",
    "reqmode", "reqtime", "approveon", "approveoff",
    "ban", "unban", "banlist", "export", "resetlinks", "restart", "update",
]

@Client.on_message(
    filters.command(_ADMIN_CMDS) & filters.private & ~filters.user(ADMINS),
    group=-1,
)
async def roast_non_admin(client: Client, message: Message):
    await message.reply_text(f"<blockquote>{_roast()}</blockquote>")
    message.stop_propagation()


# ──────────────────────────────────────────────────────────────────────────────
#  /stats  (owner only)
# ──────────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("stats") & filters.private & owner_filter)
async def stats_handler(client: Client, message: Message):
    data       = await CosmicBotz.stats()
    uptime_str = _format_uptime(client.uptime)
    await message.reply_text(
        "<b>📊 ʙᴏᴛ sᴛᴀᴛɪsᴛɪᴄs</b>\n\n"
        "<blockquote>"
        f"❍ ᴜsᴇʀs      : <b>{data['users']}</b>\n"
        f"❍ ᴄʜᴀɴɴᴇʟs  : <b>{data['channels']}</b>\n"
        f"❍ ʟɪɴᴋs ɢᴇɴ : <b>{data.get('total_links', 0)}</b>\n"
        f"❍ ᴜᴘᴛɪᴍᴇ    : <b>{uptime_str}</b>"
        "</blockquote>"
    )


# ──────────────────────────────────────────────────────────────────────────────
#  /status  (admins)
# ──────────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("status") & filters.private & admin_filter)
async def status_handler(client: Client, message: Message):
    me         = await client.get_me()
    uptime_str = _format_uptime(client.uptime)
    data       = await CosmicBotz.stats()
    await message.reply_text(
        f"🤖 <b>@{me.username}</b> ɪs <b>ᴏɴʟɪɴᴇ</b>!\n\n"
        "<blockquote>"
        f"❍ ᴜᴘᴛɪᴍᴇ   : <b>{uptime_str}</b>\n"
        f"❍ ᴜsᴇʀs    : <b>{data['users']}</b>\n"
        f"❍ ᴄʜᴀɴɴᴇʟs : <b>{data['channels']}</b>"
        "</blockquote>"
    )


# ──────────────────────────────────────────────────────────────────────────────
#  /users  (admins)
# ──────────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("users") & filters.private & admin_filter)
async def users_handler(client: Client, message: Message):
    count = await CosmicBotz.total_users()
    await message.reply_text(
        f"<blockquote>👤 ᴛᴏᴛᴀʟ ᴜsᴇʀs: <b>{count}</b></blockquote>"
    )


# ──────────────────────────────────────────────────────────────────────────────
#  /logs  (owner only)
#  FIX: uses LOG_FILE_NAME from config (was hardcoded to "bot.log" before)
# ──────────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("logs") & filters.private & owner_filter)
async def logs_handler(client: Client, message: Message):
    if not os.path.exists(LOG_FILE_NAME) or os.path.getsize(LOG_FILE_NAME) == 0:
        await message.reply_text(
            "<blockquote>📭 ʟᴏɢ ꜰɪʟᴇ ɪs ᴇᴍᴘᴛʏ ᴏʀ ᴅᴏᴇs ɴᴏᴛ ᴇxɪsᴛ.</blockquote>"
        )
        return
    await message.reply_document(
        document=LOG_FILE_NAME,
        caption=(
            "<b>📜 ʙᴏᴛ ʟᴏɢs</b>\n\n"
            "<blockquote>"
            f"❍ ꜰɪʟᴇ : <code>{LOG_FILE_NAME}</code>\n"
            f"❍ sɪᴢᴇ : <code>{os.path.getsize(LOG_FILE_NAME) / 1024:.1f} KB</code>\n"
            f"❍ ᴛɪᴍᴇ : <code>{datetime.now().strftime('%d-%b-%y %H:%M:%S')}</code>"
            "</blockquote>"
        ),
    )


# ──────────────────────────────────────────────────────────────────────────────
#  /broadcast  (admins)
# ──────────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("broadcast") & filters.private & admin_filter)
async def broadcast_handler(client: Client, message: Message):
    if not message.reply_to_message:
        await message.reply_text(
            "<blockquote>❌ ʀᴇᴘʟʏ ᴛᴏ ᴛʜᴇ ᴍᴇssᴀɢᴇ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ʙʀᴏᴀᴅᴄᴀsᴛ, "
            "ᴛʜᴇɴ sᴇɴᴅ /broadcast.</blockquote>"
        )
        return

    to_broadcast = message.reply_to_message
    user_ids     = await CosmicBotz.get_all_users()
    total        = len(user_ids)

    status_msg = await message.reply_text(
        f"<blockquote>📡 ʙʀᴏᴀᴅᴄᴀsᴛɪɴɢ ᴛᴏ <b>{total}</b> ᴜsᴇʀs…</blockquote>"
    )

    sent = blocked = failed = 0
    start = datetime.now()

    for uid in user_ids:
        try:
            await to_broadcast.copy(uid)
            sent += 1
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
            try:
                await to_broadcast.copy(uid)
                sent += 1
            except Exception:
                failed += 1
        except (UserIsBlocked, InputUserDeactivated):
            blocked += 1
        except Exception:
            failed += 1

        if (sent + blocked + failed) % 50 == 0:
            try:
                await status_msg.edit_text(
                    "<blockquote>"
                    f"📡 ᴘʀᴏɢʀᴇss:\n"
                    f"✅ sᴇɴᴛ: <b>{sent}</b>  "
                    f"❌ ꜰᴀɪʟᴇᴅ: <b>{failed}</b>  "
                    f"🚫 ʙʟᴏᴄᴋᴇᴅ: <b>{blocked}</b>"
                    "</blockquote>"
                )
            except Exception:
                pass

    elapsed = (datetime.now() - start).seconds
    await status_msg.edit_text(
        "<b>✅ ʙʀᴏᴀᴅᴄᴀsᴛ ᴄᴏᴍᴘʟᴇᴛᴇ!</b>\n\n"
        "<blockquote>"
        f"❍ sᴇɴᴛ    : <b>{sent}</b>\n"
        f"❍ ʙʟᴏᴄᴋᴇᴅ : <b>{blocked}</b>\n"
        f"❍ ꜰᴀɪʟᴇᴅ  : <b>{failed}</b>\n"
        f"❍ ᴛɪᴍᴇ    : <b>{elapsed}s</b>"
        "</blockquote>"
    )


# ──────────────────────────────────────────────────────────────────────────────
#  /cleanup  (admins)
# ──────────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("cleanup") & filters.private & admin_filter)
async def cleanup_handler(client: Client, message: Message):
    user_ids   = await CosmicBotz.get_all_users()
    status_msg = await message.reply_text(
        f"<blockquote>🧹 ᴄʜᴇᴄᴋɪɴɢ <b>{len(user_ids)}</b> ᴜsᴇʀs…</blockquote>"
    )
    removed = 0
    for uid in user_ids:
        try:
            await client.send_chat_action(uid, "typing")
        except (UserIsBlocked, InputUserDeactivated):
            await CosmicBotz.remove_user(uid)
            removed += 1
        except Exception:
            pass

    await status_msg.edit_text(
        "<b>✅ ᴄʟᴇᴀɴᴜᴘ ᴅᴏɴᴇ!</b>\n\n"
        "<blockquote>"
        f"❍ ʀᴇᴍᴏᴠᴇᴅ   : <b>{removed}</b>\n"
        f"❍ ʀᴇᴍᴀɪɴɪɴɢ : <b>{await CosmicBotz.total_users()}</b>"
        "</blockquote>"
    )


# ──────────────────────────────────────────────────────────────────────────────
#  Uptime formatter
# ──────────────────────────────────────────────────────────────────────────────

def _format_uptime(start: datetime) -> str:
    delta = datetime.now() - start
    h, rem = divmod(int(delta.total_seconds()), 3600)
    m, s   = divmod(rem, 60)
    d, h   = divmod(h, 24)
    parts  = []
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    parts.append(f"{m}m {s}s")
    return " ".join(parts)


# ──────────────────────────────────────────────────────────────────────────────
#  /ban <user_id> [reason]
# ──────────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("ban") & filters.private & admin_filter)
async def ban_handler(client: Client, message: Message):
    user_id = None
    reason = "No reason provided"
    args = message.command[1:]

    if message.reply_to_message and message.reply_to_message.from_user:
        user_id = message.reply_to_message.from_user.id
        if args:
            reason = " ".join(args)
    elif args:
        try:
            user_id = int(args[0])
            if len(args) > 1:
                reason = " ".join(args[1:])
        except ValueError:
            await message.reply_text("❌ <b>Invalid user ID.</b> Must be an integer.")
            return

    if not user_id:
        await message.reply_text(
            "❌ <b>Usage:</b> <code>/ban &lt;user_id&gt; [reason]</code> or reply to a user with <code>/ban [reason]</code>"
        )
        return

    if user_id in ADMINS:
        await message.reply_text("❌ <b>Cannot ban an administrator.</b>")
        return

    await CosmicBotz.ban_user(user_id, reason=reason, banned_by=message.from_user.id)
    await message.reply_text(
        f"🚫 <b>User Banned</b>\n\n"
        f"<blockquote>"
        f"❍ ᴜsᴇʀ ɪᴅ : <code>{user_id}</code>\n"
        f"❍ ʀᴇᴀsᴏɴ  : {reason}\n"
        f"❍ ʙʏ      : {message.from_user.mention}"
        f"</blockquote>"
    )
    logger.info("User %s banned by admin %s (reason: %s).", user_id, message.from_user.id, reason)
    await send_log(
        client,
        f"🚫 <b>User Banned</b>\n\n"
        f"<blockquote>"
        f"❍ ᴜsᴇʀ ɪᴅ : <code>{user_id}</code>\n"
        f"❍ ʀᴇᴀsᴏɴ  : {reason}\n"
        f"❍ ʙʏ      : {message.from_user.mention} (<code>{message.from_user.id}</code>)"
        f"</blockquote>"
    )


# ──────────────────────────────────────────────────────────────────────────────
#  /unban <user_id>
# ──────────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("unban") & filters.private & admin_filter)
async def unban_handler(client: Client, message: Message):
    user_id = None
    args = message.command[1:]

    if message.reply_to_message and message.reply_to_message.from_user:
        user_id = message.reply_to_message.from_user.id
    elif args:
        try:
            user_id = int(args[0])
        except ValueError:
            await message.reply_text("❌ <b>Invalid user ID.</b> Must be an integer.")
            return

    if not user_id:
        await message.reply_text(
            "❌ <b>Usage:</b> <code>/unban &lt;user_id&gt;</code> or reply to a user with <code>/unban</code>"
        )
        return

    if not await CosmicBotz.is_user_banned(user_id):
        await message.reply_text(f"ℹ️ User <code>{user_id}</code> is not banned.")
        return

    await CosmicBotz.unban_user(user_id)
    await message.reply_text(
        f"✅ <b>User Unbanned</b>\n\n"
        f"<blockquote>"
        f"❍ ᴜsᴇʀ ɪᴅ : <code>{user_id}</code>\n"
        f"❍ ʙʏ      : {message.from_user.mention}"
        f"</blockquote>"
    )
    logger.info("User %s unbanned by admin %s.", user_id, message.from_user.id)
    await send_log(
        client,
        f"✅ <b>User Unbanned</b>\n\n"
        f"<blockquote>"
        f"❍ ᴜsᴇʀ ɪᴅ : <code>{user_id}</code>\n"
        f"❍ ʙʏ      : {message.from_user.mention} (<code>{message.from_user.id}</code>)"
        f"</blockquote>"
    )


# ──────────────────────────────────────────────────────────────────────────────
#  /banlist
# ──────────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("banlist") & filters.private & admin_filter)
async def banlist_handler(client: Client, message: Message):
    banned = await CosmicBotz.get_all_banned()
    if not banned:
        await message.reply_text("<blockquote>📭 ɴᴏ ᴜsᴇʀs ᴀʀᴇ ᴄᴜʀʀᴇɴᴛʟʏ ʙᴀɴɴᴇᴅ.</blockquote>")
        return

    lines = [f"<b>🚫 Banned Users ({len(banned)} total):</b>\n"]
    for doc in banned[:50]:
        uid = doc["_id"]
        reason = doc.get("reason", "No reason")
        banned_at = datetime.fromtimestamp(doc.get("banned_at", 0)).strftime("%d-%b-%y %H:%M")
        lines.append(f"• <code>{uid}</code> — <i>{reason}</i> ({banned_at})")

    if len(banned) > 50:
        lines.append(f"\n<i>...and {len(banned) - 50} more.</i>")

    await message.reply_text("\n".join(lines))


# ──────────────────────────────────────────────────────────────────────────────
#  /export  — Export channel data as JSON document
# ──────────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("export") & filters.private & admin_filter)
async def export_handler(client: Client, message: Message):
    channels = await CosmicBotz.get_all_channels()
    if not channels:
        await message.reply_text("<blockquote>📭 ɴᴏ ᴄʜᴀɴɴᴇʟs ᴛᴏ ᴇxᴘᴏʀᴛ.</blockquote>")
        return

    wait = await message.reply_text("⏳ <i>Exporting channel data…</i>")
    export_file = f"channels_export_{int(datetime.now().timestamp())}.json"
    try:
        export_data = {
            "exported_at": datetime.now().isoformat(),
            "total_channels": len(channels),
            "channels": channels,
        }
        with open(export_file, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        await message.reply_document(
            document=export_file,
            caption=(
                "<b>📦 Channel Data Export</b>\n\n"
                f"<blockquote>"
                f"❍ ᴛᴏᴛᴀʟ   : <b>{len(channels)}</b> ᴄʜᴀɴɴᴇʟs\n"
                f"❍ ꜰᴏʀᴍᴀᴛ : JSON\n"
                f"❍ ᴛɪᴍᴇ   : {datetime.now().strftime('%d-%b-%y %H:%M:%S')}"
                f"</blockquote>"
            ),
        )
    finally:
        if os.path.exists(export_file):
            try:
                os.remove(export_file)
            except Exception:
                pass
        await wait.delete()


# ──────────────────────────────────────────────────────────────────────────────
#  /resetlinks [<channel_id> | all]
# ──────────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("resetlinks") & filters.private & admin_filter)
async def resetlinks_handler(client: Client, message: Message):
    args = message.command[1:]
    if not args:
        await message.reply_text(
            "<b>Usage:</b>\n"
            "• <code>/resetlinks &lt;channel_id&gt;</code> — Reset single channel\n"
            "• <code>/resetlinks all</code> — Reset all channels"
        )
        return

    target = args[0].strip().lower()
    if target == "all":
        await CosmicBotz.reset_all_link_counts()
        await message.reply_text("<blockquote>🔄 <b>All channel link counters have been reset to 0.</b></blockquote>")
        logger.info("All channel link counters reset by %s.", message.from_user.id)
        await send_log(client, f"🔄 <b>Link Counters Reset (ALL)</b> by {message.from_user.mention}")
        return

    try:
        ch_id = int(target)
    except ValueError:
        await message.reply_text("❌ Channel ID must be an integer or 'all'.")
        return

    if not await CosmicBotz.is_channel_exist(ch_id):
        await message.reply_text(f"❌ Channel <code>{ch_id}</code> not found in database.")
        return

    await CosmicBotz.reset_link_count(ch_id)
    await message.reply_text(f"<blockquote>🔄 <b>Link counter for channel <code>{ch_id}</code> reset to 0.</b></blockquote>")
    logger.info("Link counter for channel %s reset by %s.", ch_id, message.from_user.id)


# ──────────────────────────────────────────────────────────────────────────────
#  /restart  (admins)
# ──────────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("restart") & filters.private & admin_filter)
async def restart_handler(client: Client, message: Message):
    sent = await message.reply_text(
        "<b>🔄 Restarting bot…</b>\n\n"
        "<blockquote>Please wait a few seconds. The bot will update this message once online.</blockquote>"
    )

    try:
        with open(RESTART_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "chat_id": message.chat.id,
                "message_id": sent.id,
                "time": datetime.now().timestamp(),
            }, f)
    except Exception as e:
        logger.warning("Could not save restart state: %s", e)

    await send_log(
        client,
        f"🔄 <b>Bot restart initiated</b> by {message.from_user.mention} (<code>{message.from_user.id}</code>)."
    )

    await asyncio.sleep(1)
    os.execl(sys.executable, sys.executable, *sys.argv)


# ──────────────────────────────────────────────────────────────────────────────
#  /update  (owner only) — Universal: deploy webhook trigger + robust git pull
# ──────────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("update") & filters.private & owner_filter)
async def update_handler(client: Client, message: Message):
    status_msg = await message.reply_text("⏳ <i>Checking for updates…</i>")

    # 1. Check if DEPLOY_HOOK_URL is configured (e.g. Koyeb / Render / Heroku deploy webhook)
    db_hook = await CosmicBotz.get_setting("DEPLOY_HOOK_URL")
    hook_url = str(db_hook if db_hook is not None else getattr(config, "DEPLOY_HOOK_URL", "")).strip()

    if hook_url:
        try:
            headers = {
                "User-Agent": "LinkShareBot/2.0",
                "Content-Type": "application/json",
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(hook_url, json={}, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                    if resp.status in (200, 201, 202, 204):
                        await status_msg.edit_text(
                            "<b>🚀 Cloud Hosting Redeployment Triggered!</b>\n\n"
                            f"<blockquote>"
                            f"❍ ʜᴏsᴛɪɴɢ : <b>Cloud Redeploy (Koyeb / Render)</b>\n"
                            f"❍ sᴛᴀᴛᴜs   : <b>HTTP {resp.status} OK</b>\n"
                            f"❍ ᴀᴄᴛɪᴏɴ   : Server is fetching latest commit & rebuilding application."
                            f"</blockquote>\n\n"
                            "<i>The bot will automatically switch to the new deployment once the build completes.</i>"
                        )
                        await send_log(client, f"🚀 <b>Deploy Webhook Triggered</b> by owner (HTTP {resp.status} OK)")
                        return
                    else:
                        resp_text = (await resp.text())[:180]
                        logger.warning("Deploy hook responded with status %s: %s", resp.status, resp_text)
                        await status_msg.edit_text(
                            f"⚠️ <b>Deploy Webhook Warning:</b> Received HTTP {resp.status}\n"
                            f"<blockquote>{resp_text}</blockquote>\n\n"
                            "<i>Falling back to local Git update…</i>"
                        )
        except Exception as e:
            logger.error("Failed to trigger deploy hook: %s", e)
            await status_msg.edit_text(
                f"⚠️ <b>Deploy Webhook Error:</b> <code>{e}</code>\n\n"
                "<i>Falling back to local Git update…</i>"
            )

    # 2. Local Git update (VPS, local machine, or self-hosted server)
    git_bin = shutil.which("git")
    if not git_bin:
        await status_msg.edit_text(
            "❌ <b>Git is not installed or not found in system PATH.</b>\n\n"
            "<blockquote>"
            "❍ <b>Cloud Hosting (Koyeb, Render, etc.):</b>\n"
            "Configure your deploy webhook in <code>/config</code> under <b>DEPLOY_HOOK_URL</b> to trigger cloud redeployments.\n\n"
            "❍ <b>VPS / Linux:</b>\n"
            "Install git via: <code>sudo apt-get install git</code>"
            "</blockquote>"
        )
        return

    # Verify if inside a git work tree
    try:
        proc = await asyncio.create_subprocess_exec(
            git_bin, "rev-parse", "--is-inside-work-tree",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if stdout.decode().strip() != "true":
            await status_msg.edit_text(
                "❌ <b>Not a Git repository.</b>\n\n"
                "<blockquote>"
                "This bot installation was not deployed via <code>git clone</code>.\n"
                "If hosting on Koyeb / Render, set <b>DEPLOY_HOOK_URL</b> in <code>/config</code>."
                "</blockquote>"
            )
            return
    except Exception as e:
        await status_msg.edit_text(f"❌ <b>Git check failed:</b> <code>{e}</code>")
        return

    # Detect current branch
    try:
        proc = await asyncio.create_subprocess_exec(
            git_bin, "rev-parse", "--abbrev-ref", "HEAD",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        branch = stdout.decode().strip() or "Master"
    except Exception:
        branch = "Master"

    # Fetch latest commits from remote
    await status_msg.edit_text(f"⏳ <i>Fetching updates from origin/{branch}…</i>")
    try:
        proc = await asyncio.create_subprocess_exec(
            git_bin, "fetch", "origin", branch,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            err = stderr.decode().strip() or stdout.decode().strip()
            await status_msg.edit_text(f"❌ <b>Git fetch failed:</b>\n<code>{err}</code>")
            return
    except Exception as e:
        await status_msg.edit_text(f"❌ <b>Git fetch error:</b> <code>{e}</code>")
        return

    # Check commit count difference
    try:
        proc = await asyncio.create_subprocess_exec(
            git_bin, "rev-list", f"HEAD..origin/{branch}", "--count",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        behind_count = int(stdout.decode().strip() or "0")
    except Exception:
        behind_count = 0

    if behind_count == 0:
        # Get latest commit info
        proc = await asyncio.create_subprocess_exec(
            git_bin, "log", "-1", "--format=%h - %s (%cr)",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        cur_commit = stdout.decode().strip()
        await status_msg.edit_text(
            "<b>✅ Bot is already up to date!</b>\n\n"
            f"<blockquote>"
            f"❍ ʙʀᴀɴᴄʜ  : <code>{branch}</code>\n"
            f"❍ ᴄᴏᴍᴍɪᴛ  : <code>{cur_commit}</code>\n"
            f"❍ sᴛᴀᴛᴜs  : <b>Running latest code</b>"
            f"</blockquote>"
        )
        return

    # Retrieve incoming commit log summary
    proc = await asyncio.create_subprocess_exec(
        git_bin, "log", f"HEAD..origin/{branch}", "--oneline", "-n", "5",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    summary = stdout.decode().strip()

    # Check if requirements.txt changed
    proc = await asyncio.create_subprocess_exec(
        git_bin, "diff", f"HEAD..origin/{branch}", "--name-only",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    diff_files = stdout.decode().splitlines()

    # Reset hard to origin/branch to eliminate merge conflicts
    proc = await asyncio.create_subprocess_exec(
        git_bin, "reset", "--hard", f"origin/{branch}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        err = stderr.decode().strip() or stdout.decode().strip()
        await status_msg.edit_text(f"❌ <b>Git reset failed:</b>\n<code>{err}</code>")
        return

    # Update dependencies if requirements.txt modified
    if any("requirements.txt" in f for f in diff_files):
        await status_msg.edit_text("📦 <i>New dependencies detected. Updating requirements…</i>")
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "pip", "install", "--no-cache-dir", "-r", "requirements.txt",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
        except Exception as e:
            logger.warning("pip install during update failed: %s", e)

    # Edit message to inform user about restart
    await status_msg.edit_text(
        "<b>✅ Updates Applied Successfully!</b>\n\n"
        f"<blockquote>"
        f"❍ ʙʀᴀɴᴄʜ      : <code>{branch}</code>\n"
        f"❍ ɴᴇᴡ ᴄᴏᴍᴍɪᴛs : <b>{behind_count}</b>\n"
        f"<pre>{summary}</pre>"
        f"</blockquote>\n\n"
        "<i>Restarting bot to load new code…</i>"
    )
    await send_log(
        client,
        f"📦 <b>Bot Updated & Restarting ({behind_count} commits)</b>\n\n"
        f"<blockquote><pre>{summary}</pre></blockquote>"
    )

    try:
        with open(RESTART_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "chat_id": message.chat.id,
                "message_id": status_msg.id,
                "time": datetime.now().timestamp(),
            }, f)
    except Exception:
        pass

    await asyncio.sleep(1)
    os.execl(sys.executable, sys.executable, *sys.argv)


"""
plugins/req_mode.py
~~~~~~~~~~~~~~~~~~~
Join-request auto-approval with rich user notification.

When a join request is approved (auto or manual), the user gets a DM:
  • Channel's profile picture (if available) as photo
  • Caption with channel name, welcome note, and auto-delete warning
  • Inline button linking directly to the channel
  • The notification message is auto-deleted after LINK_EXPIRY_SECONDS

Commands:
  /reqmode  <channel_id>              — Toggle ON/OFF for one channel
  /reqtime  [<channel_id>] <seconds>  — Set timer (no id = ALL channels)
  /approveon                          — Enable all channels
  /approveoff                         — Disable all channels
"""
import asyncio

from pyrogram import Client, filters
from pyrogram.types import ChatJoinRequest, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import ADMINS, LINK_EXPIRY_SECONDS, LOGGER
from database import CosmicBotz
from helper_func import safe_delete

logger = LOGGER(__name__)
admin_filter = filters.user(ADMINS)

# How long before the approval notification is auto-deleted (same as link expiry)
_NOTIFY_DELETE_SECS = LINK_EXPIRY_SECONDS + 10


# ──────────────────────────────────────────────────────────────────────────────
#  /reqmode <channel_id>
# ──────────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("reqmode") & filters.private & admin_filter)
async def req_mode_cmd(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text(
            "<b>ᴜsᴀɢᴇ:</b> <code>/reqmode &lt;channel_id&gt;</code>\n\n"
            "<blockquote>ᴛᴏɢɢʟᴇs ᴀᴜᴛᴏ-ᴀᴘᴘʀᴏᴠᴀʟ ᴏꜰ ᴊᴏɪɴ ʀᴇǫᴜᴇsᴛs ᴏɴ/ᴏꜰꜰ.\n"
            "ᴜsᴇ /approveon ᴏʀ /approveoff ᴛᴏ ᴛᴏɢɢʟᴇ ᴀʟʟ ᴀᴛ ᴏɴᴄᴇ.</blockquote>"
        )
        return

    try:
        ch_id = int(message.command[1])
    except ValueError:
        await message.reply_text("<blockquote>❌ ᴄʜᴀɴɴᴇʟ ɪᴅ ᴍᴜsᴛ ʙᴇ ᴀɴ ɪɴᴛᴇɢᴇʀ.</blockquote>")
        return

    if not await CosmicBotz.is_channel_exist(ch_id):
        await message.reply_text("<blockquote>❌ ᴄʜᴀɴɴᴇʟ ɴᴏᴛ ʀᴇɢɪsᴛᴇʀᴇᴅ. ᴜsᴇ /addch ꜰɪʀsᴛ.</blockquote>")
        return

    new_state = not await CosmicBotz.get_req_mode(ch_id)
    await CosmicBotz.set_req_mode(ch_id, new_state)
    state_str = "✅ <b>ᴏɴ</b>" if new_state else "❌ <b>ᴏꜰꜰ</b>"
    await message.reply_text(
        f"<blockquote>🤖 ᴀᴜᴛᴏ-ᴀᴘᴘʀᴏᴠᴀʟ ꜰᴏʀ <code>{ch_id}</code> ɪs ɴᴏᴡ {state_str}.</blockquote>"
    )


# ──────────────────────────────────────────────────────────────────────────────
#  /reqtime [<channel_id>] <seconds>
# ──────────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("reqtime") & filters.private & admin_filter)
async def req_time_cmd(client: Client, message: Message):
    args = message.command[1:]

    if not args:
        g = await CosmicBotz.get_global_req_timer()
        await message.reply_text(
            "<b>ᴜsᴀɢᴇ:</b>\n\n"
            "<blockquote>"
            "<code>/reqtime &lt;seconds&gt;</code>  — ᴀʟʟ ᴄʜᴀɴɴᴇʟs\n"
            "<code>/reqtime &lt;channel_id&gt; &lt;seconds&gt;</code>  — ᴏɴᴇ ᴄʜᴀɴɴᴇʟ\n\n"
            f"ɢʟᴏʙᴀʟ ᴅᴇꜰᴀᴜʟᴛ: <b>{g}s</b> "
            f"({'ɪᴍᴍᴇᴅɪᴀᴛᴇ' if g == 0 else f'{g}s ᴅᴇʟᴀʏ'})"
            "</blockquote>"
        )
        return

    if len(args) == 1:
        try:
            seconds = int(args[0])
            if seconds < 0: raise ValueError
        except ValueError:
            await message.reply_text("<blockquote>❌ ᴍᴜsᴛ ʙᴇ ᴀ ɴᴏɴ-ɴᴇɢᴀᴛɪᴠᴇ ɪɴᴛᴇɢᴇʀ.</blockquote>")
            return

        channels = await CosmicBotz.get_all_channels()
        await CosmicBotz.set_global_req_timer(seconds)
        delay = "ɪᴍᴍᴇᴅɪᴀᴛᴇʟʏ" if seconds == 0 else f"ᴀꜰᴛᴇʀ <b>{seconds}s</b>"
        await message.reply_text(
            f"<b>✅ ɢʟᴏʙᴀʟ ᴛɪᴍᴇʀ ᴜᴘᴅᴀᴛᴇᴅ.</b>\n\n"
            f"<blockquote>❍ ᴀʟʟ <b>{len(channels)}</b> ᴄʜᴀɴɴᴇʟs → {delay}.\n"
            f"❍ ɴᴇᴡ ᴄʜᴀɴɴᴇʟs ᴀʟsᴏ ɪɴʜᴇʀɪᴛ ᴛʜɪs.</blockquote>"
        )
        return

    if len(args) == 2:
        try:
            ch_id   = int(args[0])
            seconds = int(args[1])
            if seconds < 0: raise ValueError
        except ValueError:
            await message.reply_text("<blockquote>❌ ɪɴᴛᴇɢᴇʀs ᴏɴʟʏ, ɴᴏɴ-ɴᴇɢᴀᴛɪᴠᴇ.</blockquote>")
            return

        if not await CosmicBotz.is_channel_exist(ch_id):
            await message.reply_text("<blockquote>❌ ᴄʜᴀɴɴᴇʟ ɴᴏᴛ ʀᴇɢɪsᴛᴇʀᴇᴅ.</blockquote>")
            return

        await CosmicBotz.set_req_timer(ch_id, seconds)
        delay = "ɪᴍᴍᴇᴅɪᴀᴛᴇʟʏ" if seconds == 0 else f"ᴀꜰᴛᴇʀ <b>{seconds}s</b>"
        await message.reply_text(
            f"<blockquote>✅ <code>{ch_id}</code> → {delay}.</blockquote>"
        )
        return

    await message.reply_text(
        "<blockquote>❌ ᴛᴏᴏ ᴍᴀɴʏ ᴀʀɢᴜᴍᴇɴᴛs.\n"
        "ᴜsᴇ /reqtime &lt;seconds&gt; ᴏʀ /reqtime &lt;id&gt; &lt;seconds&gt;</blockquote>"
    )


# ──────────────────────────────────────────────────────────────────────────────
#  /approveon / /approveoff
# ──────────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("approveon") & filters.private & admin_filter)
async def approve_on(client: Client, message: Message):
    channels = await CosmicBotz.get_all_channels()
    if not channels:
        await message.reply_text("<blockquote>📭 ɴᴏ ᴄʜᴀɴɴᴇʟs ʀᴇɢɪsᴛᴇʀᴇᴅ.</blockquote>")
        return
    for ch in channels:
        await CosmicBotz.set_req_mode(ch["_id"], True)
    await message.reply_text(
        f"<blockquote>✅ ᴀᴜᴛᴏ-ᴀᴘᴘʀᴏᴠᴀʟ <b>ᴇɴᴀʙʟᴇᴅ</b> ꜰᴏʀ ᴀʟʟ <b>{len(channels)}</b> ᴄʜᴀɴɴᴇʟ(s).</blockquote>"
    )


@Client.on_message(filters.command("approveoff") & filters.private & admin_filter)
async def approve_off(client: Client, message: Message):
    channels = await CosmicBotz.get_all_channels()
    if not channels:
        await message.reply_text("<blockquote>📭 ɴᴏ ᴄʜᴀɴɴᴇʟs ʀᴇɢɪsᴛᴇʀᴇᴅ.</blockquote>")
        return
    for ch in channels:
        await CosmicBotz.set_req_mode(ch["_id"], False)
    await message.reply_text(
        f"<blockquote>❌ ᴀᴜᴛᴏ-ᴀᴘᴘʀᴏᴠᴀʟ <b>ᴅɪsᴀʙʟᴇᴅ</b> ꜰᴏʀ ᴀʟʟ <b>{len(channels)}</b> ᴄʜᴀɴɴᴇʟ(s).</blockquote>"
    )


# ──────────────────────────────────────────────────────────────────────────────
#  ChatJoinRequest handler
#  Auto-approves if mode is ON, then sends a rich notification DM to the user.
# ──────────────────────────────────────────────────────────────────────────────

@Client.on_chat_join_request()
async def handle_join_request(client: Client, request: ChatJoinRequest):
    ch_id   = request.chat.id
    user_id = request.from_user.id

    if not await CosmicBotz.is_channel_exist(ch_id):
        return

    if not await CosmicBotz.get_req_mode(ch_id):
        return

    # Optional delay before approving
    delay = await CosmicBotz.get_req_timer(ch_id)
    if delay > 0:
        await asyncio.sleep(delay)

    try:
        await client.approve_chat_join_request(ch_id, user_id)
        logger.info("Auto-approved user %s → channel %s.", user_id, ch_id)
    except Exception as e:
        logger.warning("Auto-approve failed: user %s in %s: %s", user_id, ch_id, e)
        return

    # ── Send rich approval notification to user ───────────────────────────────
    await _send_approval_notification(client, request, ch_id)


async def _send_approval_notification(
    client: Client, request: ChatJoinRequest, ch_id: int
) -> None:
    """
    DM the approved user with:
      - Channel profile photo (if available)
      - Styled caption with channel name + welcome note
      - Inline button to open the channel directly
      - Message auto-deletes after LINK_EXPIRY_SECONDS
    """
    user_id  = request.from_user.id
    ch_name  = request.chat.title or str(ch_id)
    ch_uname = getattr(request.chat, "username", None)

    # Build channel link (public username or invite link)
    if ch_uname:
        ch_link = f"https://t.me/{ch_uname}"
    else:
        try:
            invite = await client.create_chat_invite_link(ch_id)
            ch_link = invite.invite_link
        except Exception:
            ch_link = None

    minutes = max(1, LINK_EXPIRY_SECONDS // 60)
    caption = (
        f"<b>ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ʜᴀs ʙᴇᴇɴ ᴀᴘᴘʀᴏᴠᴇᴅ!</b>\n\n"
        f"<blockquote>"
        f"❍ ᴄʜᴀɴɴᴇʟ : <b>{ch_name}</b>\n"
        f"❍ sᴛᴀᴛᴜs  : ✅ ᴀᴘᴘʀᴏᴠᴇᴅ\n\n"
        f"ᴛᴀᴘ ᴛʜᴇ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ ᴛᴏ ᴏᴘᴇɴ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ.\n\n"
        f"⚠️ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇᴅ ɪɴ <b>{minutes} ᴍɪɴ</b>."
        f"</blockquote>"
    )

    keyboard = None
    if ch_link:
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(f"➻ ᴏᴘᴇɴ {ch_name}", url=ch_link)
        ]])

    sent_msg = None

    # Try to send with channel photo first
    try:
        photos = await client.get_chat_photos(ch_id, limit=1)
        photo  = photos[0] if photos else None

        if photo:
            sent_msg = await client.send_photo(
                chat_id   = user_id,
                photo     = photo.file_id,
                caption   = caption,
                reply_markup = keyboard,
            )
        else:
            raise ValueError("no photo")

    except Exception:
        # Fall back to text-only if no photo or send fails
        try:
            sent_msg = await client.send_message(
                chat_id      = user_id,
                text         = caption,
                reply_markup = keyboard,
                disable_web_page_preview = True,
            )
        except Exception as e:
            logger.warning("Could not send approval notification to user %s: %s", user_id, e)
            return

    # Auto-delete the notification after expiry
    if sent_msg:
        loop = asyncio.get_event_loop()
        loop.call_later(
            _NOTIFY_DELETE_SECS,
            lambda: asyncio.ensure_future(safe_delete(sent_msg))
        )

"""
plugins/pro_channels.py
~~~~~~~~~~~~~~~~~~~~~~~
PRO FEATURE — Auto-link generator on bot-added-to-channel event.

When the bot is promoted to admin in any channel:
  - If promoted by OWNER (or if ADMIN_DIRECT_ADD is True):
      1. Registers the channel directly in the database.
      2. Generates both the Normal deep-link and the Request deep-link.
      3. Sends links to the bot owner (and admin) via DM.
  - If promoted by ADMIN (and ADMIN_DIRECT_ADD is False):
      1. Sends an interactive confirmation prompt to the admin via DM.
      2. If admin taps [Confirm] -> registers channel and delivers links.
      3. If admin taps [Ignore] -> discards addition without registering.

This file is completely self-contained.
Delete or remove it from the plugins/ directory at any time — it will
not affect any other feature, command, or file.

No bot username is stored in the database. Links are always built live
so they stay valid even if you change the bot.
"""

from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus, ChatType
from pyrogram.types import (
    CallbackQuery,
    ChatMemberUpdated,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

import config
from config import ADMINS, LOGGER, OWNER_ID, send_log
from database import CosmicBotz
from helper_func import build_links

logger = LOGGER(__name__)


@Client.on_chat_member_updated()
async def on_bot_added_to_channel(client: Client, update: ChatMemberUpdated):
    """
    Triggered every time ANY chat member's status changes.
    We only care when the BOT itself is promoted to admin in a channel.
    """
    new = update.new_chat_member

    # ── 1. Only act when the bot becomes admin/owner ─────────────────────
    if new is None:
        return

    # This update must be about the bot itself
    me = await client.get_me()
    if new.user.id != me.id:
        return

    # Only when status becomes admin or owner
    if new.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
        return

    chat = update.chat

    # ── 2. Only handle channels (ignore groups, private chats, etc.) ─────
    if chat.type != ChatType.CHANNEL:
        return

    channel_id = chat.id
    ch_name = chat.title or str(channel_id)
    promoter = update.from_user

    # ── 3. Security: Check if promoter is an authorized admin ─────────────
    if not promoter or promoter.id not in ADMINS:
        promoter_str = (
            f"{promoter.mention} (<code>{promoter.id}</code>)"
            if promoter else "<i>Unknown / Anonymous</i>"
        )
        logger.warning(
            "Bot added to channel %s (%s) by non-admin %s. Skipping auto-registration.",
            channel_id,
            ch_name,
            promoter.id if promoter else "Unknown",
        )

        alert_text = (
            "⚠️ <b>[Notice] Bot Added to Channel by Non-Admin</b>\n\n"
            f"<blockquote>"
            f"❍ ᴄʜᴀɴɴᴇʟ : <b>{ch_name}</b>\n"
            f"❍ ɪᴅ       : <code>{channel_id}</code>\n"
            f"❍ ᴀᴅᴅᴇᴅ ʙʏ : {promoter_str}\n"
            f"❍ sᴛᴀᴛᴜs  : <b>ɴᴏᴛ ʀᴇɢɪsᴛᴇʀᴇᴅ</b>"
            f"</blockquote>\n\n"
            f"<i>Bot remains in the channel, but auto-registration and link generation were skipped.\n"
            f"To register manually, send:</i> <code>/addch {channel_id}</code>"
        )

        try:
            await client.send_message(OWNER_ID, alert_text, disable_web_page_preview=True)
        except Exception as e:
            logger.error("Could not notify owner about non-admin channel addition: %s", e)

        await send_log(client, alert_text)
        return

    # ── 4. Determine addition policy (Owner direct vs Admin confirmation) ─
    is_owner = (promoter.id == OWNER_ID)

    # Check dynamic setting from database, fallback to config
    db_setting = await CosmicBotz.get_setting("ADMIN_DIRECT_ADD")
    admin_direct_add = (
        bool(db_setting) if db_setting is not None
        else getattr(config, "ADMIN_DIRECT_ADD", False)
    )

    # If added by Owner OR admin_direct_add is enabled: register immediately
    if is_owner or admin_direct_add:
        logger.info(
            "[Pro] Bot promoted in %s (%s) by %s (Direct Add: owner=%s, direct_cfg=%s).",
            channel_id,
            ch_name,
            promoter.id,
            is_owner,
            admin_direct_add,
        )
        await _register_and_deliver_links(
            client=client,
            channel_id=channel_id,
            ch_name=ch_name,
            promoter=promoter,
            is_owner=is_owner,
        )
        return

    # ── 5. Admin additions require confirmation ───────────────────────────
    logger.info(
        "[Pro] Bot promoted in %s (%s) by admin %s. Awaiting confirmation.",
        channel_id,
        ch_name,
        promoter.id,
    )

    confirm_kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ ᴄᴏɴꜰɪʀᴍ", callback_data=f"pro_ch:confirm:{channel_id}"),
            InlineKeyboardButton("❌ ɪɢɴᴏʀᴇ",  callback_data=f"pro_ch:ignore:{channel_id}"),
        ]
    ])

    confirm_text = (
        "⚡ <b>[Pro] Bot Added as Admin!</b>\n\n"
        f"<blockquote>"
        f"❍ ᴄʜᴀɴɴᴇʟ : <b>{ch_name}</b>\n"
        f"❍ ɪᴅ       : <code>{channel_id}</code>\n"
        f"❍ ᴀᴅᴅᴇᴅ ʙʏ : {promoter.mention} (<code>{promoter.id}</code>)\n"
        f"</blockquote>\n\n"
        "<i>Do you want to register this channel in the bot and generate invite links?</i>"
    )

    try:
        await client.send_message(
            promoter.id,
            confirm_text,
            reply_markup=confirm_kb,
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.warning(
            "[Pro] Could not send confirmation DM to admin %s for channel %s: %s",
            promoter.id, channel_id, e
        )
        # Notify owner and log channel about DM failure
        alert_text = (
            "⚠️ <b>[Notice] Channel Confirmation Request Failed</b>\n\n"
            f"<blockquote>"
            f"❍ ᴄʜᴀɴɴᴇʟ : <b>{ch_name}</b>\n"
            f"❍ ɪᴅ       : <code>{channel_id}</code>\n"
            f"❍ ᴀᴅᴅᴇᴅ ʙʏ : {promoter.mention} (<code>{promoter.id}</code>)\n"
            f"❍ sᴛᴀᴛᴜs  : <b>ᴄᴏᴜʟᴅ ɴᴏᴛ ᴅᴍ ᴀᴅᴍɪɴ</b>"
            f"</blockquote>\n\n"
            f"<i>The bot could not send a confirmation prompt to the admin (they may need to /start the bot).\n"
            f"To register manually, send:</i> <code>/addch {channel_id}</code>"
        )
        try:
            await client.send_message(OWNER_ID, alert_text, disable_web_page_preview=True)
        except Exception:
            pass
        await send_log(client, alert_text)
        return

    # Notify log channel that admin confirmation is pending
    await send_log(
        client,
        f"⚡ <b>[Pro] Bot Added as Admin (Pending Confirmation)</b>\n\n"
        f"<blockquote>"
        f"❍ ᴄʜᴀɴɴᴇʟ : <b>{ch_name}</b>\n"
        f"❍ ɪᴅ       : <code>{channel_id}</code>\n"
        f"❍ ᴀᴅᴅᴇᴅ ʙʏ : {promoter.mention} (<code>{promoter.id}</code>)\n"
        f"❍ sᴛᴀᴛᴜs  : <b>ᴀᴡᴀɪᴛɪɴɢ ᴀᴅᴍɪɴ ᴄᴏɴꜰɪʀᴍᴀᴛɪᴏɴ</b>"
        f"</blockquote>",
    )


# ──────────────────────────────────────────────────────────────────────────────
#  Callback query handler: [Confirm] / [Ignore]
# ──────────────────────────────────────────────────────────────────────────────

@Client.on_callback_query(filters.regex(r"^pro_ch:(confirm|ignore):(-?\d+)$"))
async def on_pro_channel_callback(client: Client, cq: CallbackQuery):
    action = cq.matches[0].group(1)
    channel_id = int(cq.matches[0].group(2))
    user_id = cq.from_user.id

    # Security check: must be an admin
    if user_id not in ADMINS:
        try:
            await cq.answer("❌ You are not authorized to perform this action.", show_alert=True)
        except Exception:
            pass
        return

    # Fetch live chat info if available
    ch_name = str(channel_id)
    try:
        chat = await client.get_chat(channel_id)
        ch_name = chat.title or str(channel_id)
    except Exception:
        pass

    # ── Action: Ignore ─────────────────────────────────────────────────────────
    if action == "ignore":
        try:
            await cq.edit_message_text(
                "<b>❌ ᴄʜᴀɴɴᴇʟ ᴀᴅᴅɪᴛɪᴏɴ ɪɢɴᴏʀᴇᴅ</b>\n\n"
                f"<blockquote>"
                f"❍ ᴄʜᴀɴɴᴇʟ : <b>{ch_name}</b>\n"
                f"❍ ɪᴅ       : <code>{channel_id}</code>\n"
                f"❍ sᴛᴀᴛᴜs  : <b>ɴᴏᴛ ʀᴇɢɪsᴛᴇʀᴇᴅ</b>\n"
                f"❍ ᴀᴄᴛɪᴏɴ  : ɪɢɴᴏʀᴇᴅ ʙʏ {cq.from_user.mention}"
                f"</blockquote>\n\n"
                "<i>The channel was not added to the bot database.</i>",
            )
        except Exception:
            pass

        try:
            await cq.answer("Channel addition ignored.")
        except Exception:
            pass

        await send_log(
            client,
            f"🗑 <b>Channel Addition Ignored</b>\n\n"
            f"<blockquote>"
            f"❍ ᴄʜᴀɴɴᴇʟ    : <b>{ch_name}</b> (<code>{channel_id}</code>)\n"
            f"❍ ɪɢɴᴏʀᴇᴅ ʙʏ : {cq.from_user.mention} (<code>{user_id}</code>)"
            f"</blockquote>",
        )
        return

    # ── Action: Confirm ────────────────────────────────────────────────────────
    if action == "confirm":
        # Register channel in DB
        added = await CosmicBotz.add_channel(channel_id, ch_name)
        if not added:
            await CosmicBotz.update_channel_name(channel_id, ch_name)

        # Build links
        try:
            normal_link, req_deep_link = await build_links(client, channel_id)
        except Exception as e:
            logger.error("[Pro] Failed to build links on confirm for %s: %s", channel_id, e)
            try:
                await cq.answer("⚠️ Could not generate links — ensure the bot has invite-link permission.", show_alert=True)
            except Exception:
                pass
            return

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Normal Link", url=normal_link)],
            [InlineKeyboardButton("📩 Request Link", url=req_deep_link)],
        ])

        # Edit admin's confirmation message to display the links
        try:
            await cq.edit_message_text(
                f"⚡ <b>[Pro] Channel Added!</b>\n\n"
                f"✅ Cʜᴀᴛ <b>{ch_name}</b> (<code>{channel_id}</code>) ʜᴀs ʙᴇᴇɴ ᴀᴅᴅᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ.\n\n"
                f"🔗 Nᴏʀᴍᴀʟ Lɪɴᴋ:\n<code>{normal_link}</code>\n\n"
                f"🔗 Rᴇǫᴜᴇsᴛ Lɪɴᴋ:\n<code>{req_deep_link}</code>",
                reply_markup=keyboard,
                disable_web_page_preview=True,
            )
        except Exception:
            pass

        try:
            await cq.answer("✅ Channel registered successfully!")
        except Exception:
            pass

        # Send links to Owner if confirming admin is not the owner
        if user_id != OWNER_ID:
            try:
                await client.send_message(
                    OWNER_ID,
                    f"⚡ <b>[Pro] Channel Confirmed by Admin!</b>\n\n"
                    f"✅ Cʜᴀᴛ <b>{ch_name}</b> (<code>{channel_id}</code>) "
                    f"ʜᴀs ʙᴇᴇɴ ᴄᴏɴꜰɪʀᴍᴇᴅ ʙʏ ᴀᴅᴍɪɴ {cq.from_user.mention} (<code>{user_id}</code>).\n\n"
                    f"🔗 Nᴏʀᴍᴀʟ Lɪɴᴋ:\n<code>{normal_link}</code>\n\n"
                    f"🔗 Rᴇǫᴜᴇsᴛ Lɪɴᴋ:\n<code>{req_deep_link}</code>",
                    reply_markup=keyboard,
                    disable_web_page_preview=True,
                )
            except Exception as e:
                logger.error("[Pro] Could not notify owner about confirmed channel %s: %s", channel_id, e)

        await send_log(
            client,
            f"⚡ <b>[Pro] Channel Confirmed & Added</b>\n\n"
            f"✅ Cʜᴀᴛ <b>{ch_name}</b> (<code>{channel_id}</code>) "
            f"ʜᴀs ʙᴇᴇɴ ᴄᴏɴꜰɪʀᴍᴇᴅ ʙʏ ᴀᴅᴍɪɴ {cq.from_user.mention} (<code>{user_id}</code>).\n\n"
            f"🔗 Nᴏʀᴍᴀʟ: <code>{normal_link}</code>\n"
            f"📩 Rᴇǫᴜᴇsᴛ: <code>{req_deep_link}</code>",
            reply_markup=keyboard,
        )


# ──────────────────────────────────────────────────────────────────────────────
#  Internal helper: Direct registration & link distribution
# ──────────────────────────────────────────────────────────────────────────────

async def _register_and_deliver_links(
    client: Client,
    channel_id: int,
    ch_name: str,
    promoter,
    is_owner: bool,
):
    # Register channel (no-op if already registered, refreshes name)
    added = await CosmicBotz.add_channel(channel_id, ch_name)
    if not added:
        await CosmicBotz.update_channel_name(channel_id, ch_name)

    # Build both links
    try:
        normal_link, req_deep_link = await build_links(client, channel_id)
    except Exception as e:
        logger.error("[Pro] Failed to build links for %s: %s", channel_id, e)
        try:
            await client.send_message(
                OWNER_ID,
                f"⚡ <b>[Pro] Bot added to channel</b>\n\n"
                f"📢 <b>{ch_name}</b> (<code>{channel_id}</code>)\n\n"
                "⚠️ Could not generate links — ensure the bot has invite-link permission.",
            )
        except Exception:
            pass
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Normal Link", url=normal_link)],
        [InlineKeyboardButton("📩 Request Link", url=req_deep_link)],
    ])

    owner_text = (
        f"⚡ <b>[Pro] Bot added as admin!</b>\n\n"
        f"✅ Cʜᴀᴛ <b>{ch_name}</b> (<code>{channel_id}</code>) "
        f"ʜᴀs ʙᴇᴇɴ ᴀᴅᴅᴇᴅ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ.\n\n"
        f"🔗 Nᴏʀᴍᴀʟ Lɪɴᴋ:\n<code>{normal_link}</code>\n\n"
        f"🔗 Rᴇǫᴜᴇsᴛ Lɪɴᴋ:\n<code>{req_deep_link}</code>"
    )

    try:
        await client.send_message(
            OWNER_ID,
            owner_text,
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )
        logger.info("[Pro] Notified owner with both links for channel %s.", channel_id)
    except Exception as e:
        logger.error("[Pro] Could not DM owner for channel %s: %s", channel_id, e)

    # If added directly by admin, send links to the admin as well
    if not is_owner and promoter:
        try:
            await client.send_message(
                promoter.id,
                owner_text,
                reply_markup=keyboard,
                disable_web_page_preview=True,
            )
            logger.info("[Pro] Sent links to admin %s for channel %s.", promoter.id, channel_id)
        except Exception as e:
            logger.warning("[Pro] Could not DM admin %s for channel %s: %s", promoter.id, channel_id, e)

    promoter_str = (
        f"{promoter.mention} (<code>{promoter.id}</code>)"
        if promoter else "<i>Unknown / Anonymous</i>"
    )
    await send_log(
        client,
        f"⚡ <b>[Pro] Bot added as admin!</b>\n\n"
        f"✅ Cʜᴀᴛ <b>{ch_name}</b> (<code>{channel_id}</code>) "
        f"ʜᴀs ʙᴇᴇɴ ᴀᴅᴅᴇᴅ ʙʏ {promoter_str}.\n\n"
        f"🔗 Nᴏʀᴍᴀʟ: <code>{normal_link}</code>\n"
        f"📩 Rᴇǫᴜᴇsᴛ: <code>{req_deep_link}</code>",
        reply_markup=keyboard,
    )

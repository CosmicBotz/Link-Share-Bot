"""
plugins/settings.py
~~~~~~~~~~~~~~~~~~~
/config — Interactive settings panel for the bot owner.

Lets you view and edit runtime-configurable settings directly from Telegram.
Changes are stored in MongoDB (settings collection) and applied immediately.

NON-EDITABLE (core credentials — must stay in .env):
  APP_ID, API_HASH, TG_BOT_TOKEN, DB_URL

EDITABLE via this panel:
  FORCE_SUB_CHANNEL   — channel ID for force-subscribe gate (0 = off)
  LINK_EXPIRY_SECONDS — how long temp invite links live
  RATE_LIMIT_MAX      — max link requests per window
  RATE_LIMIT_WINDOW   — rate-limit window in seconds
  START_PICS          — comma-separated image URLs for /start
  START_TEXT          — custom start message (HTML)
  HELP_TEXT           — custom help message (HTML)
  ABOUT_TEXT          — custom about message (HTML)
  ADMINS_EXTRA        — extra admin user IDs (space-separated)

All values are read at runtime from DB; .env values are used as fallback.
"""
import asyncio

from pyrogram import Client, filters
from pyrogram.errors import QueryIdInvalid
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import LOGGER, OWNER_ID
from database import CosmicBotz

logger = LOGGER(__name__)
owner_filter = filters.user([OWNER_ID])

# ── Settings registry ─────────────────────────────────────────────────────────
# Each entry: (key, label, type_hint, description)
_SETTINGS: list[tuple[str, str, str, str]] = [
    ("FORCE_SUB_CHANNEL",   "ꜰᴏʀᴄᴇ sᴜʙ ᴄʜᴀɴɴᴇʟ",  "int",  "ᴄʜᴀɴɴᴇʟ ɪᴅ (0 = ᴅɪsᴀʙʟᴇᴅ)"),
    ("LINK_EXPIRY_SECONDS", "ʟɪɴᴋ ᴇxᴘɪʀʏ (sᴇᴄs)",  "int",  "sᴇᴄᴏɴᴅs ʙᴇꜰᴏʀᴇ ɪɴᴠɪᴛᴇ ʟɪɴᴋ ᴇxᴘɪʀᴇs"),
    ("RATE_LIMIT_MAX",      "ʀᴀᴛᴇ ʟɪᴍɪᴛ (ʀᴇǫᴜᴇsᴛs)", "int",  "ᴍᴀx ʟɪɴᴋ ʀᴇǫᴜᴇsᴛs ᴘᴇʀ ᴡɪɴᴅᴏᴡ"),
    ("RATE_LIMIT_WINDOW",   "ʀᴀᴛᴇ ʟɪᴍɪᴛ (sᴇᴄs)",   "int",  "ʀᴀᴛᴇ-ʟɪᴍɪᴛ ᴡɪɴᴅᴏᴡ ɪɴ sᴇᴄᴏɴᴅs"),
    ("START_PICS",          "sᴛᴀʀᴛ ᴘɪᴄs",           "str",  "ᴄᴏᴍᴍᴀ-sᴇᴘᴀʀᴀᴛᴇᴅ ɪᴍᴀɢᴇ ᴜʀʟs"),
    ("START_TEXT",          "sᴛᴀʀᴛ ᴛᴇxᴛ",           "text", "ʜᴛᴍʟ sᴛᴀʀᴛ ᴍᴇssᴀɢᴇ ({mention} sᴜᴘᴘᴏʀᴛᴇᴅ)"),
    ("HELP_TEXT",           "ʜᴇʟᴘ ᴛᴇxᴛ",            "text", "ʜᴛᴍʟ ʜᴇʟᴘ ᴍᴇssᴀɢᴇ"),
    ("ABOUT_TEXT",          "ᴀʙᴏᴜᴛ ᴛᴇxᴛ",           "text", "ʜᴛᴍʟ ᴀʙᴏᴜᴛ ᴍᴇssᴀɢᴇ"),
    ("ADMINS_EXTRA",        "ᴇxᴛʀᴀ ᴀᴅᴍɪɴs",         "str",  "sᴘᴀᴄᴇ-sᴇᴘᴀʀᴀᴛᴇᴅ ᴜsᴇʀ ɪᴅs"),
    ("LOG_CHANNEL",         "ʟᴏɢ ᴄʜᴀɴɴᴇʟ",          "int",  "ᴄʜᴀɴɴᴇʟ ɪᴅ ꜰᴏʀ ʟᴏɢs (0 = ᴅɪsᴀʙʟᴇᴅ)"),
    ("ADMIN_DIRECT_ADD",    "ᴀᴅᴍɪɴ ᴅɪʀᴇᴄᴛ ᴀᴅᴅ",     "bool", "ᴀᴅᴍɪɴ ᴀᴅᴅᴇᴅ ᴄʜᴀɴɴᴇʟs ᴀᴅᴅ ᴅɪʀᴇᴄᴛʟʏ ᴡɪᴛʜᴏᴜᴛ ᴄᴏɴꜰɪʀᴍᴀᴛɪᴏɴ"),
    ("DEPLOY_HOOK_URL",     "ᴅᴇᴘʟᴏʏ ʜᴏᴏᴋ ᴜʀʟ",      "str",  "ᴡᴇʙʜᴏᴏᴋ ᴜʀʟ ꜰᴏʀ ᴋᴏʏᴇʙ/ʀᴇɴᴅᴇʀ ʀᴇᴅᴇᴘʟᴏʏ"),
]

_SETTING_KEYS = {s[0] for s in _SETTINGS}

# Track which key and panel message is pending input: user_id → (key, panel_message_id)
_awaiting_input: dict[int, tuple[str, int]] = {}


# ──────────────────────────────────────────────────────────────────────────────
#  /config  — open the settings panel
# ──────────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("config") & filters.private & owner_filter)
async def config_handler(client: Client, message: Message):
    await _send_settings_panel(client, message)


async def _send_settings_panel(client, target, edit: bool = False):
    """Build and send (or edit) the settings panel."""
    current = await CosmicBotz.get_all_settings()

    rows = []
    for key, label, type_hint, desc in _SETTINGS:
        val = current.get(key)
        # Format display value
        if type_hint == "bool":
            import config as _cfg
            val_bool = val if val is not None else getattr(_cfg, key, False)
            display = "ᴇɴᴀʙʟᴇᴅ" if val_bool else "ᴅɪsᴀʙʟᴇᴅ"
        elif val is None:
            display = "ɴᴏᴛ sᴇᴛ"
        elif isinstance(val, str) and len(val) > 20:
            display = val[:17] + "…"
        else:
            display = str(val)
        rows.append([InlineKeyboardButton(
            f"❍ {label}  [{display}]",
            callback_data=f"cfg:edit:{key}"
        )])

    rows.append([
        InlineKeyboardButton("🔄 ʀᴇꜰʀᴇsʜ",       callback_data="cfg:refresh"),
        InlineKeyboardButton("🗑 ʀᴇsᴇᴛ ᴀʟʟ",    callback_data="cfg:resetall"),
    ])
    rows.append([InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="cfg:close")])

    text = (
        "<b>⚙️ ʙᴏᴛ sᴇᴛᴛɪɴɢs</b>\n\n"
        "<blockquote>"
        "ᴛᴀᴘ ᴀ sᴇᴛᴛɪɴɢ ᴛᴏ ᴇᴅɪᴛ ɪᴛ.\n"
        "ᴄʜᴀɴɢᴇs ᴀᴘᴘʟʏ ɪᴍᴍᴇᴅɪᴀᴛᴇʟʏ — ɴᴏ ʀᴇsᴛᴀʀᴛ ɴᴇᴇᴅᴇᴅ.\n"
        "ᴄᴏʀᴇ ᴄʀᴇᴅᴇɴᴛɪᴀʟs (ᴀᴘɪ, ᴛᴏᴋᴇɴ, ᴅʙ) ᴍᴜsᴛ ʙᴇ sᴇᴛ ɪɴ .ᴇɴᴠ."
        "</blockquote>"
    )
    kb = InlineKeyboardMarkup(rows)

    if isinstance(target, Message):
        await target.reply_text(text, reply_markup=kb)
    elif isinstance(target, CallbackQuery):
        try:
            await target.edit_message_text(text, reply_markup=kb)
        except Exception:
            pass
    elif isinstance(target, int):
        try:
            await client.edit_message_text(chat_id=OWNER_ID, message_id=target, text=text, reply_markup=kb)
        except Exception:
            await client.send_message(chat_id=OWNER_ID, text=text, reply_markup=kb)
    else:
        try:
            await target.edit_message_text(text, reply_markup=kb)
        except Exception:
            pass


# ──────────────────────────────────────────────────────────────────────────────
#  Callbacks
# ──────────────────────────────────────────────────────────────────────────────

@Client.on_callback_query(filters.regex(r"^cfg:(.+)$") & owner_filter)
async def config_callback(client: Client, cq: CallbackQuery):
    data = cq.matches[0].group(1)

    # ── Refresh panel ──────────────────────────────────────────────────────────
    if data == "refresh":
        _awaiting_input.pop(cq.from_user.id, None)
        await _send_settings_panel(client, cq, edit=True)
        try: await cq.answer("ʀᴇꜰʀᴇsʜᴇᴅ.")
        except QueryIdInvalid: pass
        return

    # ── Close panel ────────────────────────────────────────────────────────────
    if data == "close":
        _awaiting_input.pop(cq.from_user.id, None)
        try:
            await cq.message.delete()
        except Exception:
            pass
        try: await cq.answer()
        except QueryIdInvalid: pass
        return

    # ── Reset ALL editable settings ────────────────────────────────────────────
    if data == "resetall":
        try:
            await cq.edit_message_reply_markup(InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ ᴄᴏɴꜰɪʀᴍ ʀᴇsᴇᴛ", callback_data="cfg:resetall:confirm"),
                InlineKeyboardButton("❌ ᴄᴀɴᴄᴇʟ",         callback_data="cfg:refresh"),
            ]]))
        except Exception:
            pass
        try: await cq.answer()
        except QueryIdInvalid: pass
        return

    if data == "resetall:confirm":
        for key, *_ in _SETTINGS:
            await CosmicBotz.delete_setting(key)
        await _send_settings_panel(client, cq, edit=True)
        try: await cq.answer("ᴀʟʟ sᴇᴛᴛɪɴɢs ʀᴇsᴇᴛ ᴛᴏ ᴅᴇꜰᴀᴜʟᴛs.")
        except QueryIdInvalid: pass
        return

    # ── Edit a specific key ────────────────────────────────────────────────────
    if data.startswith("edit:"):
        key = data.split(":", 1)[1]
        if key not in _SETTING_KEYS:
            try: await cq.answer("ᴜɴᴋɴᴏᴡɴ sᴇᴛᴛɪɴɢ.", show_alert=True)
            except QueryIdInvalid: pass
            return

        # Find the setting definition
        setting = next((s for s in _SETTINGS if s[0] == key), None)
        if not setting:
            return
        _, label, type_hint, desc = setting

        # If it's a boolean setting, toggle it immediately on tap
        if type_hint == "bool":
            import config as _cfg
            current_settings = await CosmicBotz.get_all_settings()
            cur_val = current_settings.get(key, getattr(_cfg, key, False))
            new_val = not bool(cur_val)
            await CosmicBotz.save_setting(key, new_val)
            _apply_setting_runtime(key, new_val)
            await _send_settings_panel(client, cq, edit=True)
            status_txt = "ᴇɴᴀʙʟᴇᴅ" if new_val else "ᴅɪsᴀʙʟᴇᴅ"
            try:
                await cq.answer(f"{label}: {status_txt}")
            except QueryIdInvalid:
                pass
            return

        current_val = (await CosmicBotz.get_all_settings()).get(key, "ɴᴏᴛ sᴇᴛ")

        try:
            await cq.edit_message_text(
                f"<b>⚙️ ᴇᴅɪᴛɪɴɢ: {label}</b>\n\n"
                f"<blockquote>"
                f"❍ ᴋᴇʏ         : <code>{key}</code>\n"
                f"❍ ᴛʏᴘᴇ        : <code>{type_hint}</code>\n"
                f"❍ ᴅᴇsᴄ        : {desc}\n"
                f"❍ ᴄᴜʀʀᴇɴᴛ     : <code>{current_val}</code>"
                f"</blockquote>\n\n"
                "sᴇɴᴅ ᴛʜᴇ ɴᴇᴡ ᴠᴀʟᴜᴇ ɴᴏᴡ, ᴏʀ ᴛᴀᴘ ᴄᴀɴᴄᴇʟ.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ ᴄᴀɴᴄᴇʟ", callback_data="cfg:refresh"),
                    InlineKeyboardButton("🗑 ᴄʟᴇᴀʀ ᴠᴀʟᴜᴇ", callback_data=f"cfg:clear:{key}"),
                ]]),
            )
        except Exception:
            pass

        # Mark this user as awaiting input for this key along with the panel message ID
        _awaiting_input[cq.from_user.id] = (key, cq.message.id)
        try: await cq.answer()
        except QueryIdInvalid: pass
        return

    # ── Clear a specific key ───────────────────────────────────────────────────
    if data.startswith("clear:"):
        key = data.split(":", 1)[1]
        if key in _SETTING_KEYS:
            await CosmicBotz.delete_setting(key)
            _apply_setting_runtime(key, None)
        await _send_settings_panel(client, cq, edit=True)
        try: await cq.answer(f"{key} ᴄʟᴇᴀʀᴇᴅ.")
        except QueryIdInvalid: pass
        return

    try: await cq.answer()
    except QueryIdInvalid: pass


# ──────────────────────────────────────────────────────────────────────────────
#  Intercept next message from owner when a setting is being edited
# ──────────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.private & owner_filter & ~filters.command([
    "config", "start", "help", "about", "addch", "delch", "channels",
    "links", "reqlink", "bulklink", "reqmode", "reqtime", "approveon",
    "approveoff", "stats", "status", "broadcast", "cleanup", "users",
    "logs", "ban", "unban", "banlist", "restart", "update", "export",
    "resetlinks", "top", "checkch", "ping", "id",
]), group=10)
async def settings_input_handler(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in _awaiting_input:
        return

    entry = _awaiting_input.pop(user_id)
    if isinstance(entry, tuple):
        key, panel_msg_id = entry
    else:
        key, panel_msg_id = entry, None

    # Automatically delete the owner's input text to keep the chat completely clean
    try:
        await message.delete()
    except Exception:
        pass

    raw_val = message.text.strip() if message.text else ""

    setting   = next((s for s in _SETTINGS if s[0] == key), None)
    label     = setting[1] if setting else key
    type_hint = setting[2] if setting else "str"

    if not raw_val:
        if panel_msg_id:
            await _send_settings_panel(client, panel_msg_id, edit=True)
        return

    # Validate type
    if type_hint == "int":
        try:
            parsed = int(raw_val)
        except ValueError:
            # Edit the panel message in-place to display the error with a cancel option
            if panel_msg_id:
                try:
                    await client.edit_message_text(
                        chat_id=OWNER_ID,
                        message_id=panel_msg_id,
                        text=(
                            f"<b>⚠️ ɪɴᴠᴀʟɪᴅ ɪɴᴘᴜᴛ: {label}</b>\n\n"
                            f"<blockquote>"
                            f"❌ <code>{key}</code> ʀᴇǫᴜɪʀᴇs ᴀɴ ɪɴᴛᴇɢᴇʀ.\n"
                            f"ʏᴏᴜ ᴇɴᴛᴇʀᴇᴅ: <code>{raw_val}</code>"
                            f"</blockquote>\n\n"
                            "<i>sᴇɴᴅ ᴀ ᴠᴀʟɪᴅ ɪɴᴛᴇɢᴇʀ ɴᴏᴡ, ᴏʀ ᴛᴀᴘ ᴄᴀɴᴄᴇʟ:</i>"
                        ),
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("❌ ᴄᴀɴᴄᴇʟ", callback_data="cfg:refresh"),
                            InlineKeyboardButton("🗑 ᴄʟᴇᴀʀ ᴠᴀʟᴜᴇ", callback_data=f"cfg:clear:{key}"),
                        ]]),
                    )
                except Exception:
                    pass
            _awaiting_input[user_id] = (key, panel_msg_id)
            return

        await CosmicBotz.save_setting(key, parsed)
        _apply_setting_runtime(key, parsed)
        display = str(parsed)
    else:
        await CosmicBotz.save_setting(key, raw_val)
        _apply_setting_runtime(key, raw_val)
        display = raw_val[:60] + ("…" if len(raw_val) > 60 else "")

    # Edit the panel message back to the normal settings panel (in-place)
    if panel_msg_id:
        await _send_settings_panel(client, panel_msg_id, edit=True)
    else:
        await _send_settings_panel(client, message)

    logger.info("Setting %s updated to %r by owner (panel edited in-place).", key, display)


# ──────────────────────────────────────────────────────────────────────────────
#  Runtime apply — patch in-memory modules so changes take effect immediately
#  without a restart
# ──────────────────────────────────────────────────────────────────────────────

def _apply_setting_runtime(key: str, value) -> None:
    """
    Patch the live in-memory values so the setting takes effect immediately.
    Modules import constants at startup; we patch them here.
    """
    try:
        import config as _cfg
        import rate_limit as _rl

        if key == "FORCE_SUB_CHANNEL":
            _cfg.FORCE_SUB_CHANNEL = int(value) if value is not None else 0

        elif key == "LINK_EXPIRY_SECONDS":
            _cfg.LINK_EXPIRY_SECONDS = int(value) if value is not None else 300

        elif key == "RATE_LIMIT_MAX":
            val = int(value) if value is not None else 3
            _cfg.RATE_LIMIT_MAX = val
            _rl.RATE_LIMIT_MAX  = val

        elif key == "RATE_LIMIT_WINDOW":
            val = int(value) if value is not None else 10
            _cfg.RATE_LIMIT_WINDOW = val
            _rl.RATE_LIMIT_WINDOW  = val

        elif key == "START_PICS":
            pics = [p.strip().strip('"').strip("'")
                    for p in (value or "").split(",") if p.strip()]
            _cfg.START_PICS = pics

        elif key == "START_TEXT":
            _cfg.START_TEXT = value or ""

        elif key == "HELP_TEXT":
            _cfg.HELP_TEXT = value or ""

        elif key == "ABOUT_TEXT":
            _cfg.ABOUT_TEXT = value or ""

        elif key == "ADMINS_EXTRA":
            extras = [int(x) for x in (value or "").split() if x.isdigit()]
            import config as cfg2
            # Merge with owner and existing admins
            current = list(cfg2.ADMINS)
            merged  = list({cfg2.OWNER_ID, *current, *extras})
            cfg2.ADMINS = merged

        elif key == "LOG_CHANNEL":
            _cfg.LOG_CHANNEL = int(value) if value is not None else 0

        elif key == "ADMIN_DIRECT_ADD":
            _cfg.ADMIN_DIRECT_ADD = bool(value) if value is not None else False

        elif key == "DEPLOY_HOOK_URL":
            _cfg.DEPLOY_HOOK_URL = str(value or "").strip()

    except Exception as e:
        logger.warning("Could not apply runtime setting %s: %s", key, e)

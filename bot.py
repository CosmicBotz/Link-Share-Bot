"""
bot.py
~~~~~~
PyroFork Bot client.
"""
import asyncio
import json
import os
from datetime import datetime

import pyrogram.utils
from aiohttp import web
from pyrogram import Client
from pyrogram.enums import ParseMode
from pyrogram.types import BotCommand

from config import (
    API_HASH,
    APP_ID,
    LOG_FILE_NAME,
    LOGGER,
    PORT,
    TG_BOT_TOKEN,
    TG_BOT_WORKERS,
    send_log,
)
from database import CosmicBotz
from plugins import web_server

# Allow big channel IDs (PyroFork / Pyrogram v2)
pyrogram.utils.MIN_CHANNEL_ID = -1009147483647

logger = LOGGER(__name__)


class Bot(Client):
    """Extended Pyrogram Client with startup / shutdown hooks."""

    def __init__(self):
        super().__init__(
            name="LinkShareBot",
            api_hash=API_HASH,
            api_id=APP_ID,
            plugins={"root": "plugins"},
            workers=TG_BOT_WORKERS,
            bot_token=TG_BOT_TOKEN,
            parse_mode=ParseMode.HTML,
        )

    async def start(self):
        # Install global error handler BEFORE connecting
        from plugins.errors import install_global_error_handler
        install_global_error_handler(self)

        # Initialise DB connection
        CosmicBotz.connect()

        # ── Load runtime settings from DB (override .env defaults) ────────────
        from plugins.settings import _apply_setting_runtime
        try:
            saved = await CosmicBotz.get_all_settings()
            for key, value in saved.items():
                _apply_setting_runtime(key, value)
            if saved:
                logger.info("Loaded %d runtime settings from DB.", len(saved))
        except Exception as e:
            logger.warning("Could not load runtime settings: %s", e)

        await super().start()

        me = await self.get_me()
        self.uptime   = datetime.now()
        self.username = me.username

        # ── Cache bot username to avoid get_me() calls in link-building loops ──
        # This is the FIX for the FloodWait on invoke bug.
        # build_links() reads from this cache — zero Telegram API calls per link.
        from helper_func import set_bot_username
        set_bot_username(me.username)

        logger.info("Bot @%s is running! [workers=%s]", me.username, TG_BOT_WORKERS)

        # ── Check for restart state file and notify admin ──────────────────────
        restart_file = "restart.json"
        if os.path.exists(restart_file):
            try:
                with open(restart_file, "r", encoding="utf-8") as f:
                    rdata = json.load(f)
                r_chat = rdata.get("chat_id")
                r_msg  = rdata.get("message_id")
                r_time = rdata.get("time", 0)
                diff   = f"{datetime.now().timestamp() - r_time:.1f}s" if r_time else "instant"
                if r_chat and r_msg:
                    await self.edit_message_text(
                        chat_id=r_chat,
                        message_id=r_msg,
                        text=(
                            "<b>✅ Bot Restarted Successfully!</b>\n\n"
                            f"<blockquote>"
                            f"❍ ᴛɪᴍᴇ ᴛᴀᴋᴇɴ : <b>{diff}</b>\n"
                            f"❍ sᴛᴀᴛᴜs     : <b>ᴏɴʟɪɴᴇ</b>\n"
                            f"❍ ᴜsᴇʀɴᴀᴍᴇ   : @{me.username}"
                            f"</blockquote>"
                        ),
                    )
            except Exception as e:
                logger.warning("Could not edit restart message: %s", e)
            finally:
                try:
                    os.remove(restart_file)
                except Exception:
                    pass

        # ── Notify LOG_CHANNEL on startup ──────────────────────────────────────
        await send_log(
            self,
            f"🤖 <b>Bot Online</b>\n\n"
            f"<blockquote>"
            f"❍ ᴜsᴇʀɴᴀᴍᴇ : @{me.username}\n"
            f"❍ ɪᴅ       : <code>{me.id}</code>\n"
            f"❍ ᴡᴏʀᴋᴇʀs  : {TG_BOT_WORKERS}\n"
            f"❍ ᴛɪᴍᴇ     : {self.uptime.strftime('%d-%b-%y %H:%M:%S')}"
            f"</blockquote>"
        )

        # ── Set bot command menu ───────────────────────────────────────────────
        try:
            await self.set_bot_commands([
                BotCommand("start",      "sᴛᴀʀᴛ ʙᴏᴛ"),
                BotCommand("help",       "ʜᴇʟᴘ & ᴄᴏᴍᴍᴀɴᴅs"),
                BotCommand("about",      "ᴀʙᴏᴜᴛ ᴛʜɪs ʙᴏᴛ"),
                BotCommand("ping",         "ʙᴏᴛ ʟᴀᴛᴇɴᴄʏ"),
                BotCommand("id",           "ɢᴇᴛ ɪᴅ ᴏꜰ ᴀɴʏ ᴜsᴇʀ/ᴄʜᴀᴛ/sᴇʟꜰ"),
                BotCommand("addch",        "ʀᴇɢɪsᴛᴇʀ ᴀ ᴄʜᴀɴɴᴇʟ"),
                BotCommand("delch",      "ʀᴇᴍᴏᴠᴇ ᴀ ᴄʜᴀɴɴᴇʟ"),
                BotCommand("channels",   "ᴍᴀɴᴀɢᴇ ᴄʜᴀɴɴᴇʟs"),
                BotCommand("links",      "ɴᴏʀᴍᴀʟ ᴅᴇᴇᴘ-ʟɪɴᴋs"),
                BotCommand("reqlink",    "ʀᴇǫᴜᴇsᴛ ᴅᴇᴇᴘ-ʟɪɴᴋs"),
                BotCommand("bulklink",     "ʙᴜʟᴋ ɢᴇɴᴇʀᴀᴛᴇ ʟɪɴᴋs"),
                BotCommand("checkch",      "ᴄʜᴀɴɴᴇʟ ʜᴇᴀʟᴛʜ ᴄʜᴇᴄᴋ"),
                BotCommand("top",          "ᴛᴏᴘ ᴄʜᴀɴɴᴇʟs ʙʏ ʟɪɴᴋs"),
                BotCommand("reqmode",    "ᴛᴏɢɢʟᴇ ᴀᴜᴛᴏ-ᴀᴘᴘʀᴏᴠᴇ"),
                BotCommand("reqtime",    "sᴇᴛ ᴀᴘᴘʀᴏᴠᴇ ᴅᴇʟᴀʏ"),
                BotCommand("approveon",  "ᴀᴜᴛᴏ-ᴀᴘᴘʀᴏᴠᴇ ᴀʟʟ ᴏɴ"),
                BotCommand("approveoff", "ᴀᴜᴛᴏ-ᴀᴘᴘʀᴏᴠᴇ ᴀʟʟ ᴏꜰꜰ"),
                BotCommand("stats",      "ʙᴏᴛ sᴛᴀᴛɪsᴛɪᴄs"),
                BotCommand("status",     "ʙᴏᴛ sᴛᴀᴛᴜs"),
                BotCommand("broadcast",  "ʙʀᴏᴀᴅᴄᴀsᴛ ᴍᴇssᴀɢᴇ"),
                BotCommand("cleanup",    "ʀᴇᴍᴏᴠᴇ ɪɴᴀᴄᴛɪᴠᴇ ᴜsᴇʀs"),
                BotCommand("users",      "ᴜsᴇʀ ᴄᴏᴜɴᴛ"),
                BotCommand("config",     "⚙️ ʙᴏᴛ sᴇᴛᴛɪɴɢs ᴘᴀɴᴇʟ"),
                BotCommand("ban",        "ʙᴀɴ ᴀ ᴜsᴇʀ"),
                BotCommand("unban",      "ᴜɴʙᴀɴ ᴀ ᴜsᴇʀ"),
                BotCommand("banlist",    "ʟɪsᴛ ʙᴀɴɴᴇᴅ ᴜsᴇʀs"),
                BotCommand("export",     "ᴇxᴘᴏʀᴛ ᴄʜᴀɴɴᴇʟ ᴅᴀᴛᴀ"),
                BotCommand("resetlinks", "ʀᴇsᴇᴛ ʟɪɴᴋ ᴄᴏᴜɴᴛs"),
                BotCommand("restart",    "ʀᴇsᴛᴀʀᴛ ʙᴏᴛ"),
                BotCommand("update",     "ᴜᴘᴅᴀᴛᴇ ʙᴏᴛ"),
                BotCommand("logs",       "ᴅᴏᴡɴʟᴏᴀᴅ ʟᴏɢs"),
            ])
            logger.info("Bot commands menu set.")
        except Exception as e:
            logger.warning("Failed to set bot commands: %s", e)

        # ── Health-check web server ────────────────────────────────────────────
        runner = web.AppRunner(await web_server())
        await runner.setup()
        await web.TCPSite(runner, "0.0.0.0", PORT).start()
        logger.info("Web server listening on port %s.", PORT)

    async def stop(self, *args):
        await super().stop()
        logger.info("Bot stopped cleanly.")

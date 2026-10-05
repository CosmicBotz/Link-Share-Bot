import asyncio
import traceback

from pyrogram import Client
from pyrogram.errors import (
    FloodWait,
    InputUserDeactivated,
    MessageDeleteForbidden,
    MessageIdInvalid,
    MessageNotModified,
    PeerIdInvalid,
    QueryIdInvalid,
    UserIsBlocked,
)

from config import LOGGER, OWNER_ID, send_log

logger = LOGGER(__name__)

# ── Errors we swallow silently (expected, non-critical) ──────────────────────
_SILENT = (
    MessageNotModified,
    MessageIdInvalid,
    MessageDeleteForbidden,
    QueryIdInvalid,
    UserIsBlocked,
    InputUserDeactivated,
    PeerIdInvalid,
)


# ──────────────────────────────────────────────────────────────────────────────
#  Central error handler — called whenever we catch something unexpected
# ──────────────────────────────────────────────────────────────────────────────

async def _on_error(client: Client, exc: Exception) -> None:
    if isinstance(exc, FloodWait):
        logger.warning("ꜰʟᴏᴏᴅᴡᴀɪᴛ %ss — sleeping.", exc.value)
        await asyncio.sleep(exc.value + 1)
        return

    if isinstance(exc, _SILENT):
        logger.debug("Suppressed: %s — %s", type(exc).__name__, exc)
        return

    tb = traceback.format_exc()
    logger.error("Unhandled exception:\n%s", tb)

    err_text = (
        f"<b>⚠️ ᴜɴʜᴀɴᴅʟᴇᴅ ᴇʀʀᴏʀ</b>\n\n"
        f"<blockquote><code>{type(exc).__name__}: {str(exc)[:300]}</code></blockquote>\n\n"
        f"<i>Full traceback in logs. Bot is still running.</i>"
    )

    try:
        await client.send_message(OWNER_ID, err_text)
    except Exception:
        pass

    await send_log(client, err_text)


# ──────────────────────────────────────────────────────────────────────────────
#  Safe handler wrapper — wraps a single handler coroutine
# ──────────────────────────────────────────────────────────────────────────────

def _make_safe(client: Client, coro_func):
    """
    Return a wrapped version of an async handler function that catches
    all exceptions and routes them through _on_error.
    """
    async def wrapper(*args, **kwargs):
        try:
            return await coro_func(*args, **kwargs)
        except FloodWait as e:
            logger.warning("ꜰʟᴏᴏᴅᴡᴀɪᴛ %ss in handler %s.", e.value, coro_func.__name__)
            await asyncio.sleep(e.value + 1)
        except _SILENT as e:
            logger.debug("Suppressed in handler %s: %s", coro_func.__name__, e)
        except Exception as e:
            await _on_error(client, e)
    wrapper.__name__ = coro_func.__name__
    return wrapper


# ──────────────────────────────────────────────────────────────────────────────
#  install_global_error_handler
#  Called once from bot.py AFTER super().__init__() and BEFORE super().start()
# ──────────────────────────────────────────────────────────────────────────────

def install_global_error_handler(client: Client) -> None:
    """
    Patch the correct internal method so every handler is wrapped in
    try/except without touching each plugin individually.

    Tries three different hook points in order (PyroFork may expose any of them):
      1. client.dispatcher.update_workers  — task-level wrap (cleanest)
      2. Pyrogram internal _run_handler     — per-handler wrap
      3. Manual wrap of all registered handlers via client.dispatcher.groups
    """
    installed = False

    # ── Strategy 1: patch Dispatcher._process_update ─────────────────────────
    try:
        dispatcher = client.dispatcher
        original_process = dispatcher.__class__._process_update

        async def safe_process_update(self, client_, update, users, chats):
            try:
                return await original_process(self, client_, update, users, chats)
            except FloodWait as e:
                logger.warning("ꜰʟᴏᴏᴅᴡᴀɪᴛ %ss in _process_update.", e.value)
                await asyncio.sleep(e.value + 1)
            except _SILENT as e:
                logger.debug("Suppressed in _process_update: %s", e)
            except Exception as e:
                await _on_error(client_, e)

        dispatcher.__class__._process_update = safe_process_update
        logger.info("ɢʟᴏʙᴀʟ ᴇʀʀᴏʀ ʜᴀɴᴅʟᴇʀ installed via Dispatcher._process_update.")
        installed = True
    except AttributeError:
        pass

    if installed:
        return

    # ── Strategy 2: patch Dispatcher.process_update (older naming) ───────────
    try:
        dispatcher = client.dispatcher
        original_process = dispatcher.__class__.process_update

        async def safe_process_update_v2(self, client_, update, users, chats):
            try:
                return await original_process(self, client_, update, users, chats)
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
            except _SILENT as e:
                logger.debug("Suppressed: %s", e)
            except Exception as e:
                await _on_error(client_, e)

        dispatcher.__class__.process_update = safe_process_update_v2
        logger.info("ɢʟᴏʙᴀʟ ᴇʀʀᴏʀ ʜᴀɴᴅʟᴇʀ installed via Dispatcher.process_update.")
        installed = True
    except AttributeError:
        pass

    if installed:
        return

    # ── Strategy 3: wrap client.invoke for RPC-level FloodWait ───────────────
    try:
        original_invoke = client.__class__.invoke

        async def safe_invoke(self, query, retries=5, timeout=15, sleep_threshold=None):
            try:
                return await original_invoke(self, query, retries, timeout, sleep_threshold)
            except FloodWait as e:
                logger.warning("ꜰʟᴏᴏᴅᴡᴀɪᴛ %ss on invoke.", e.value)
                await asyncio.sleep(e.value + 1)
                return await safe_invoke(self, query, retries, timeout, sleep_threshold)
            except Exception:
                raise  # let handlers deal with the rest

        client.__class__.invoke = safe_invoke
        logger.info("ꜰʟᴏᴏᴅᴡᴀɪᴛ guard installed via Client.invoke (partial protection).")
        installed = True
    except AttributeError:
        pass

    if not installed:
        logger.warning(
            "ɢʟᴏʙᴀʟ ᴇʀʀᴏʀ ʜᴀɴᴅʟᴇʀ: could not find a suitable hook point in this "
            "PyroFork/Pyrogram version. Handlers are NOT globally wrapped. "
            "Each plugin uses its own try/except instead."
        )


# ──────────────────────────────────────────────────────────────────────────────
#  Disconnect hook
# ──────────────────────────────────────────────────────────────────────────────

@Client.on_disconnect()
async def on_disconnect(client: Client):
    logger.warning("ʙᴏᴛ ᴅɪsᴄᴏɴɴᴇᴄᴛᴇᴅ — Pyrogram will auto-reconnect.")

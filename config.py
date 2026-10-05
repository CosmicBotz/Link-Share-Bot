import logging
import os
from logging.handlers import RotatingFileHandler

# ──────────────────────────────────────────────
#  Logging setup
# ──────────────────────────────────────────────
LOG_FILE_NAME = "links-sharingbot.txt"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    handlers=[
        RotatingFileHandler(
            LOG_FILE_NAME,
            maxBytes=50_000_000,
            backupCount=10,
        ),
        logging.StreamHandler(),
    ],
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)


def LOGGER(name: str) -> logging.Logger:
    return logging.getLogger(name)


# ──────────────────────────────────────────────
#  Internal env helper
# ──────────────────────────────────────────────

def _env(key: str, default=None, required: bool = False):
    val = os.environ.get(key, default)
    if required and not val:
        raise ValueError(f"Environment variable '{key}' is required but not set.")
    return val


# ──────────────────────────────────────────────
#  Telegram credentials
# ──────────────────────────────────────────────
APP_ID:       int = int(_env("APP_ID", required=True))
API_HASH:     str = _env("API_HASH", required=True)
TG_BOT_TOKEN: str = _env("TG_BOT_TOKEN", required=True)

# ──────────────────────────────────────────────
#  Access control
# ──────────────────────────────────────────────
OWNER_ID: int = int(_env("OWNER_ID", required=True))

_raw_admins = _env("ADMINS", default="").split()
ADMINS: list[int] = list({OWNER_ID, *[int(x) for x in _raw_admins if x.isdigit()]})

# ──────────────────────────────────────────────
#  MongoDB
# ──────────────────────────────────────────────
DB_URL:  str = _env("DB_URL", required=True)
DB_NAME: str = _env("DB_NAME", default="LinkShareBot")

# ──────────────────────────────────────────────
#  Deployment / performance
# ──────────────────────────────────────────────
TG_BOT_WORKERS: int = int(_env("TG_BOT_WORKERS", default=100))
PORT:           int = int(_env("PORT", default=8080))

# ──────────────────────────────────────────────
#  Force-subscription channel (0 = disabled)
# ──────────────────────────────────────────────
FORCE_SUB_CHANNEL: int = int(_env("FORCE_SUB_CHANNEL", default=0))

# ──────────────────────────────────────────────
#  Invite link expiry (seconds, default 5 min)
# ──────────────────────────────────────────────
LINK_EXPIRY_SECONDS: int = int(_env("LINK_EXPIRY_SECONDS", default=300))

# ──────────────────────────────────────────────
#  Start picture(s)
#  Comma-separated image URLs.  Can be Telegraph links, CDN links, etc.
#  One URL is picked at random on every /start.
#
#  Example in your .env / Render env var:
#    START_PICS=https://telegra.ph/file/abc.jpg,https://telegra.ph/file/def.jpg
#
#  Leave empty → text-only /start.
# ──────────────────────────────────────────────
_raw_pics = _env("START_PICS", default="").strip()
# Split by comma, strip whitespace/quotes from each entry, drop empties
START_PICS: list[str] = [
    p.strip().strip('"').strip("'")
    for p in _raw_pics.split(",")
    if p.strip().strip('"').strip("'")
]

# ──────────────────────────────────────────────
#  Custom bot texts  (HTML is fully supported)
#  If a variable is empty the built-in defaults in start.py are used.
# ──────────────────────────────────────────────
START_TEXT: str = _env("START_TEXT", default="")
HELP_TEXT:  str = _env("HELP_TEXT",  default="")
ABOUT_TEXT: str = _env("ABOUT_TEXT", default="")

# ──────────────────────────────────────────────
#  Log channel / Hosting deployment
# ──────────────────────────────────────────────
LOG_CHANNEL:     int = int(_env("LOG_CHANNEL", default=0))
DEPLOY_HOOK_URL: str = _env("DEPLOY_HOOK_URL", default="").strip()

# ──────────────────────────────────────────────
#  Channel Auto-Registration Policy
#  False = Admins must confirm via button prompt (default)
#  True  = Admins add channels directly like Owner
# ──────────────────────────────────────────────
ADMIN_DIRECT_ADD: bool = str(_env("ADMIN_DIRECT_ADD", default="False")).lower() in ("true", "1", "yes")


async def send_log(client, text: str, reply_markup=None):
    """Safely forward a notification message to LOG_CHANNEL if configured."""
    if not LOG_CHANNEL:
        return
    try:
        await client.send_message(
            chat_id=LOG_CHANNEL,
            text=text,
            reply_markup=reply_markup,
            disable_web_page_preview=True,
        )
    except Exception as e:
        LOGGER("config").warning("Failed to send message to LOG_CHANNEL (%s): %s", LOG_CHANNEL, e)


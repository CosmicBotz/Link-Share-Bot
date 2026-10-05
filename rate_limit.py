"""
helper_func/rate_limit.py  (or just rate_limit.py at project root)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In-memory rate limiter for link generation requests.

Rules:
  - Max RATE_LIMIT_MAX requests per RATE_LIMIT_WINDOW seconds per user.
  - Defaults: 3 requests / 10 seconds (configurable in config.py).
  - Completely in-memory — resets on bot restart. No DB writes.
  - Thread-safe for asyncio (single-threaded event loop).

Usage (in start.py before generating a link):
    from rate_limit import check_rate_limit

    allowed, wait_secs = check_rate_limit(user_id)
    if not allowed:
        await message.reply_text(f"...try again in {wait_secs}s")
        return
"""
import time
from collections import defaultdict, deque

from config import LOGGER

logger = LOGGER(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
RATE_LIMIT_MAX    = 3   # max requests
RATE_LIMIT_WINDOW = 10  # per N seconds

# ── State: user_id → deque of timestamps ──────────────────────────────────────
_buckets: dict[int, deque] = defaultdict(deque)


def check_rate_limit(user_id: int) -> tuple[bool, int]:
    """
    Check if user_id is within rate limit.

    Returns:
        (True,  0)          — allowed, proceed
        (False, wait_secs)  — blocked, tell user to wait this many seconds

    Automatically cleans up old timestamps on each call.
    """
    now    = time.monotonic()
    bucket = _buckets[user_id]

    # Drop timestamps outside the current window
    while bucket and now - bucket[0] > RATE_LIMIT_WINDOW:
        bucket.popleft()

    if len(bucket) >= RATE_LIMIT_MAX:
        # How long until the oldest request falls out of the window
        wait = int(RATE_LIMIT_WINDOW - (now - bucket[0])) + 1
        logger.debug("Rate-limited user %s — wait %ss.", user_id, wait)
        return False, wait

    bucket.append(now)
    return True, 0


def get_remaining(user_id: int) -> int:
    """Return how many requests user_id has left in the current window."""
    now    = time.monotonic()
    bucket = _buckets[user_id]
    while bucket and now - bucket[0] > RATE_LIMIT_WINDOW:
        bucket.popleft()
    return max(0, RATE_LIMIT_MAX - len(bucket))


def reset_user(user_id: int) -> None:
    """Manually clear rate-limit bucket for a user (e.g. after admin override)."""
    _buckets.pop(user_id, None)

"""
LinkBypass Pro Bot — Configuration
=====================================
Central configuration for the Telegram link bypass bot.
All environment variables and constants are managed here.
"""

import os
import logging

# ── Logging Setup ──────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(name)-25s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("LinkBypassBot")

# ── Telegram ──────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))
BOT_USERNAME = os.getenv("BOT_USERNAME", "LinkBypassProBot")

# ── Database ───────────────────────────────────────────────
DB_PATH = os.getenv("DB_PATH", "data/linkbypass.db")

# ── Web Server (for Render health checks) ─────────────────
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("PORT", "10000"))

# ── Bypass Engine Config ──────────────────────────────────
# Timeouts (seconds)
REDIRECT_TIMEOUT = int(os.getenv("REDIRECT_TIMEOUT", "15"))
PATTERN_TIMEOUT = int(os.getenv("PATTERN_TIMEOUT", "20"))
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "25"))
BROWSER_TIMEOUT = int(os.getenv("BROWSER_TIMEOUT", "30"))
HEADLESS_TIMEOUT = int(os.getenv("HEADLESS_TIMEOUT", "65"))
GLOBAL_BYPASS_TIMEOUT = int(os.getenv("GLOBAL_BYPASS_TIMEOUT", "90"))

# Max redirect hops
MAX_REDIRECTS = int(os.getenv("MAX_REDIRECTS", "15"))

# External API keys (optional — enhances bypass success rate)
LINKBYPASS_API_KEY = os.getenv("LINKBYPASS_API_KEY", "")
BYPASS_VIP_API_KEY = os.getenv("BYPASS_VIP_API_KEY", "")
ADBYPASS_API_KEY = os.getenv("ADBYPASS_API_KEY", "")

# User-Agent rotation pool
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
]

# Referer pool for bypass requests
REFERER_POOL = [
    "https://www.google.com/",
    "https://www.google.co.in/",
    "https://t.me/",
    "https://www.facebook.com/",
    "https://twitter.com/",
    "https://www.youtube.com/",
    "https://www.reddit.com/",
]

# ── Rate Limiting Defaults ─────────────────────────────────
DEFAULT_FREE_DAILY_LIMIT = 15
DEFAULT_PREMIUM_DAILY_LIMIT = 999
DEFAULT_COOLDOWN_SECONDS = 5
DEFAULT_BATCH_FREE = 5
DEFAULT_BATCH_PREMIUM = 25

# ── Premium Defaults ────────────────────────────────────────
DEFAULT_STARS_PRICE = 150
DEFAULT_STARS_DAYS = 30
DEFAULT_REFERRAL_COUNT = 3
DEFAULT_REFERRAL_DAYS = 3

# ── Version ────────────────────────────────────────────────
BOT_VERSION = "4.1.0"
BOT_NAME = "LinkBypass Pro"

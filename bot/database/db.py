"""
LinkBypass Pro — Database Layer
================================
Complete async SQLite database with all tables, indexes,
migrations, and helper functions for the entire bot.
"""

import aiosqlite
import secrets
import time as _time
import logging
import datetime
from typing import Optional, Dict, List, Any, Tuple

from bot.config import DB_PATH

logger = logging.getLogger(__name__)

_db: Optional[aiosqlite.Connection] = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Connection Management
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def get_db() -> aiosqlite.Connection:
    """Get or create the database connection (singleton)."""
    global _db
    if _db is None:
        import os
        os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)
        _db = await aiosqlite.connect(DB_PATH)
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA synchronous=NORMAL")
        await _db.execute("PRAGMA cache_size=-8000")  # 8MB cache
        await _db.execute("PRAGMA foreign_keys=ON")
        await init_db()
    return _db


async def close_db():
    """Close the database connection cleanly."""
    global _db
    if _db:
        await _db.close()
        _db = None
        logger.info("Database connection closed")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Schema Initialization
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def init_db():
    """Initialize all database tables and default data."""
    db = await get_db()

    # ── Core Tables ────────────────────────────────────────
    await db.executescript("""

    -- Users table: stores all Telegram users who interact with the bot
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT DEFAULT '',
        full_name TEXT DEFAULT '',
        language TEXT DEFAULT 'en',
        is_premium INTEGER DEFAULT 0,
        premium_until TIMESTAMP NULL,
        premium_source TEXT NULL,
        daily_bypasses_used INTEGER DEFAULT 0,
        total_bypasses INTEGER DEFAULT 0,
        referral_code TEXT UNIQUE,
        referred_by INTEGER NULL,
        total_referrals INTEGER DEFAULT 0,
        bonus_credits INTEGER DEFAULT 0,
        is_banned INTEGER DEFAULT 0,
        ban_reason TEXT NULL,
        last_bypass REAL DEFAULT 0,
        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Bypass history: every link bypass attempt is logged here
    CREATE TABLE IF NOT EXISTS bypass_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        original_url TEXT NOT NULL,
        shortener TEXT DEFAULT 'unknown',
        destination_url TEXT DEFAULT '',
        final_url TEXT DEFAULT '',
        method TEXT DEFAULT 'unknown',
        layer INTEGER DEFAULT 0,
        time_taken REAL DEFAULT 0.0,
        success INTEGER DEFAULT 1,
        error_message TEXT NULL,
        injected_url TEXT NULL,
        shortener_used_for_inject TEXT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );

    -- Shortener configs: admin-configured shortener APIs for link injection/monetization
    CREATE TABLE IF NOT EXISTS shortener_configs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shortener_name TEXT UNIQUE NOT NULL,
        display_name TEXT NOT NULL,
        api_key TEXT NOT NULL DEFAULT '',
        api_endpoint TEXT NOT NULL DEFAULT '',
        api_format TEXT DEFAULT 'json_shortenedUrl',
        is_active INTEGER DEFAULT 0,
        intercept_percent INTEGER DEFAULT 30,
        total_links_created INTEGER DEFAULT 0,
        total_clicks INTEGER DEFAULT 0,
        priority INTEGER DEFAULT 5,
        last_tested TIMESTAMP NULL,
        last_test_result TEXT NULL,
        last_test_response_ms INTEGER NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Force subscribe channels
    CREATE TABLE IF NOT EXISTS force_sub_channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_username TEXT UNIQUE NOT NULL,
        channel_id INTEGER NULL,
        channel_title TEXT NULL,
        is_active INTEGER DEFAULT 1,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Daily analytics
    CREATE TABLE IF NOT EXISTS analytics_daily (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date DATE UNIQUE NOT NULL,
        total_users INTEGER DEFAULT 0,
        new_users INTEGER DEFAULT 0,
        active_users INTEGER DEFAULT 0,
        total_bypasses INTEGER DEFAULT 0,
        successful_bypasses INTEGER DEFAULT 0,
        failed_bypasses INTEGER DEFAULT 0,
        total_injected_links INTEGER DEFAULT 0,
        premium_purchases INTEGER DEFAULT 0,
        new_referrals INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Supported shorteners catalog
    CREATE TABLE IF NOT EXISTS supported_shorteners (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        domain TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        bypass_method TEXT NOT NULL DEFAULT 'auto',
        pattern_module TEXT NULL,
        category TEXT DEFAULT 'general',
        is_working INTEGER DEFAULT 1,
        success_count INTEGER DEFAULT 0,
        fail_count INTEGER DEFAULT 0,
        avg_time_ms REAL DEFAULT 0,
        last_tested TIMESTAMP NULL,
        last_test_result TEXT NULL,
        notes TEXT NULL
    );

    -- Shortener bypass statistics (aggregated per shortener domain)
    CREATE TABLE IF NOT EXISTS shortener_stats (
        shortener TEXT PRIMARY KEY,
        total_bypasses INTEGER DEFAULT 0,
        successful INTEGER DEFAULT 0,
        failed INTEGER DEFAULT 0,
        avg_time_ms REAL DEFAULT 0,
        last_success TIMESTAMP NULL,
        last_failure TIMESTAMP NULL,
        last_error TEXT NULL
    );

    -- Broadcast queue for admin mass messaging
    CREATE TABLE IF NOT EXISTS broadcast_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_text TEXT NOT NULL,
        message_type TEXT DEFAULT 'text',
        media_file_id TEXT NULL,
        total_target INTEGER DEFAULT 0,
        sent_count INTEGER DEFAULT 0,
        failed_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending',
        started_at TIMESTAMP NULL,
        finished_at TIMESTAMP NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Settings: key-value store for all bot configuration
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        description TEXT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Ad configurations for optional ad injection
    CREATE TABLE IF NOT EXISTS ad_config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ad_text TEXT NOT NULL,
        ad_url TEXT NOT NULL,
        ad_type TEXT DEFAULT 'inline',
        is_active INTEGER DEFAULT 1,
        show_every_n INTEGER DEFAULT 5,
        impressions INTEGER DEFAULT 0,
        clicks INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- API usage tracking for external bypass APIs
    CREATE TABLE IF NOT EXISTS api_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        api_name TEXT NOT NULL,
        endpoint TEXT NOT NULL,
        status_code INTEGER DEFAULT 0,
        response_time_ms REAL DEFAULT 0,
        success INTEGER DEFAULT 0,
        error_message TEXT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- User feedback and reports
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        feedback_type TEXT DEFAULT 'general',
        url TEXT NULL,
        message TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        admin_reply TEXT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Bypass cache: cache successful bypasses to avoid re-processing
    CREATE TABLE IF NOT EXISTS bypass_cache (
        original_url TEXT PRIMARY KEY,
        destination_url TEXT NOT NULL,
        method TEXT NOT NULL,
        shortener TEXT DEFAULT 'unknown',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP NOT NULL,
        hit_count INTEGER DEFAULT 0
    );

    """)

    # ── Indexes ────────────────────────────────────────────
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_users_created ON users(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_users_premium ON users(is_premium)",
        "CREATE INDEX IF NOT EXISTS idx_users_referral ON users(referral_code)",
        "CREATE INDEX IF NOT EXISTS idx_users_referred_by ON users(referred_by)",
        "CREATE INDEX IF NOT EXISTS idx_history_user ON bypass_history(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_history_created ON bypass_history(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_history_shortener ON bypass_history(shortener)",
        "CREATE INDEX IF NOT EXISTS idx_history_method ON bypass_history(method)",
        "CREATE INDEX IF NOT EXISTS idx_history_success ON bypass_history(success)",
        "CREATE INDEX IF NOT EXISTS idx_cache_expires ON bypass_cache(expires_at)",
        "CREATE INDEX IF NOT EXISTS idx_api_usage_created ON api_usage(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_api_usage_api ON api_usage(api_name)",
        "CREATE INDEX IF NOT EXISTS idx_analytics_date ON analytics_daily(date)",
        "CREATE INDEX IF NOT EXISTS idx_supported_domain ON supported_shorteners(domain)",
    ]
    for idx_sql in indexes:
        await db.execute(idx_sql)

    # ── Default Settings ───────────────────────────────────
    defaults = {
        # Rate limiting
        'free_daily_limit': '15',
        'premium_daily_limit': '999',
        'cooldown_seconds': '5',
        'batch_limit_free': '5',
        'batch_limit_premium': '25',

        # Premium
        'premium_stars_price': '150',
        'premium_stars_days': '30',
        'premium_stars_enabled': 'true',
        'premium_referral_count': '3',
        'premium_referral_days': '3',
        'premium_referral_enabled': 'true',

        # Features
        'inject_links_enabled': 'false',
        'force_sub_enabled': 'false',
        'antispam_enabled': 'true',
        'cache_enabled': 'true',
        'cache_ttl_hours': '24',
        'ads_enabled': 'false',
        'maintenance_mode': 'false',

        # Referrals
        'referral_bonus_credits': '5',

        # Shortener injection
        'shortener_rotation_mode': 'round_robin',
        'inject_percent': '30',

        # Signup
        'signup_bonus': '5',
        'signup_enabled': 'true',

        # Messages
        'welcome_message': '',
        'maintenance_message': 'Bot is under maintenance. Please try again later.',

        # Bypass engine
        'max_retries': '2',
        'prefer_api_bypass': 'true',
        'enable_layer5_headless': 'false',
    }
    for k, v in defaults.items():
        await db.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v)
        )

    await db.commit()
    logger.info("Database initialized successfully")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Settings CRUD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get a setting value by key."""
    db = await get_db()
    cur = await db.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = await cur.fetchone()
    return row['value'] if row else default


async def set_setting(key: str, value: str, description: str = None):
    """Set a setting value (upsert)."""
    db = await get_db()
    if description:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value, description, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            (key, str(value), description)
        )
    else:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (key, str(value))
        )
    await db.commit()


async def get_all_settings() -> Dict[str, str]:
    """Get all settings as a dictionary."""
    db = await get_db()
    cur = await db.execute("SELECT key, value FROM settings ORDER BY key")
    rows = await cur.fetchall()
    return {r['key']: r['value'] for r in rows}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# User CRUD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def get_or_create_user(user_id: int, tg_user=None, full_name: str = None) -> dict:
    """Get existing user or create a new one. Returns user dict."""
    db = await get_db()
    cur = await db.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = await cur.fetchone()

    if not user:
        uname = ""
        fname = full_name or ""
        if tg_user is not None:
            if hasattr(tg_user, 'username'):
                uname = tg_user.username or ""
                fname = tg_user.full_name or ""
            elif isinstance(tg_user, str):
                uname = tg_user

        ref_code = secrets.token_hex(4)
        await db.execute(
            """INSERT INTO users (user_id, username, full_name, referral_code)
               VALUES (?, ?, ?, ?)""",
            (user_id, uname, fname, ref_code)
        )
        await db.commit()
        cur = await db.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        user = await cur.fetchone()
        logger.info(f"New user created: {user_id} ({fname})")

    return dict(user)


async def get_user(user_id: int) -> Optional[dict]:
    """Get a user by ID, returns None if not found."""
    db = await get_db()
    cur = await db.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = await cur.fetchone()
    return dict(row) if row else None


async def update_user(user_id: int, **kwargs):
    """Update user fields dynamically."""
    if not kwargs:
        return
    db = await get_db()
    sets = ", ".join(f"{k}=?" for k in kwargs)
    values = list(kwargs.values()) + [user_id]
    await db.execute(f"UPDATE users SET {sets} WHERE user_id=?", values)
    await db.commit()


async def ban_user(user_id: int, reason: str = "No reason"):
    """Ban a user."""
    await update_user(user_id, is_banned=1, ban_reason=reason)


async def unban_user(user_id: int):
    """Unban a user."""
    await update_user(user_id, is_banned=0, ban_reason=None)


async def is_user_premium(user_id: int) -> bool:
    """Check if user has active premium."""
    user = await get_user(user_id)
    if not user:
        return False
    if not user['is_premium']:
        return False
    if user['premium_until']:
        try:
            until = datetime.datetime.fromisoformat(str(user['premium_until']))
            if until < datetime.datetime.now():
                await update_user(user_id, is_premium=0)
                return False
        except (ValueError, TypeError):
            pass
    return True


async def grant_premium(user_id: int, days: int, source: str = "admin"):
    """Grant premium to a user for N days."""
    until = datetime.datetime.now() + datetime.timedelta(days=days)
    await update_user(
        user_id,
        is_premium=1,
        premium_until=until.isoformat(),
        premium_source=source
    )


async def increment_daily_bypass(user_id: int):
    """Increment daily and total bypass counters."""
    db = await get_db()
    await db.execute(
        """UPDATE users SET
           daily_bypasses_used = daily_bypasses_used + 1,
           total_bypasses = total_bypasses + 1,
           last_bypass = ?,
           last_active = CURRENT_TIMESTAMP
           WHERE user_id = ?""",
        (_time.time(), user_id)
    )
    await db.commit()


async def reset_daily_bypasses():
    """Reset all users' daily bypass counters (call daily at midnight)."""
    db = await get_db()
    await db.execute("UPDATE users SET daily_bypasses_used = 0")
    await db.commit()
    logger.info("Daily bypass counters reset for all users")


async def get_user_count() -> int:
    """Get total user count."""
    db = await get_db()
    cur = await db.execute("SELECT COUNT(*) as cnt FROM users")
    row = await cur.fetchone()
    return row['cnt']


async def get_all_user_ids() -> List[int]:
    """Get all user IDs for broadcasting."""
    db = await get_db()
    cur = await db.execute("SELECT user_id FROM users WHERE is_banned=0")
    return [row['user_id'] for row in await cur.fetchall()]


async def get_top_users(limit: int = 10) -> List[dict]:
    """Get top users by total bypasses."""
    db = await get_db()
    cur = await db.execute(
        "SELECT * FROM users ORDER BY total_bypasses DESC LIMIT ?", (limit,)
    )
    return [dict(r) for r in await cur.fetchall()]


async def get_recent_users(limit: int = 20) -> List[dict]:
    """Get most recently joined users."""
    db = await get_db()
    cur = await db.execute(
        "SELECT * FROM users ORDER BY created_at DESC LIMIT ?", (limit,)
    )
    return [dict(r) for r in await cur.fetchall()]


async def search_user(user_id: int) -> Optional[dict]:
    """Search for a user by ID with extra stats."""
    user = await get_user(user_id)
    if not user:
        return None
    db = await get_db()
    # Get bypass count
    cur = await db.execute(
        "SELECT COUNT(*) as cnt FROM bypass_history WHERE user_id=?", (user_id,)
    )
    bypass_count = (await cur.fetchone())['cnt']
    user['bypass_history_count'] = bypass_count
    return user


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Referral System
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def process_referral(new_user_id: int, referral_code: str) -> Optional[dict]:
    """Process a referral: link new user to referrer, increment referrer stats."""
    db = await get_db()
    # Find referrer
    cur = await db.execute("SELECT * FROM users WHERE referral_code=?", (referral_code,))
    referrer = await cur.fetchone()
    if not referrer:
        return None
    if referrer['user_id'] == new_user_id:
        return None  # Can't refer yourself

    # Check if already referred
    user = await get_user(new_user_id)
    if user and user.get('referred_by'):
        return None

    # Update new user
    await update_user(new_user_id, referred_by=referrer['user_id'])

    # Update referrer
    bonus = int(await get_setting('referral_bonus_credits', '5'))
    await db.execute(
        """UPDATE users SET
           total_referrals = total_referrals + 1,
           bonus_credits = bonus_credits + ?
           WHERE user_id = ?""",
        (bonus, referrer['user_id'])
    )

    # Check if referrer should get premium
    ref_enabled = await get_setting('premium_referral_enabled', 'true')
    ref_count = int(await get_setting('premium_referral_count', '3'))
    ref_days = int(await get_setting('premium_referral_days', '3'))

    if ref_enabled == 'true':
        cur2 = await db.execute("SELECT total_referrals FROM users WHERE user_id=?", (referrer['user_id'],))
        ref_row = await cur2.fetchone()
        if ref_row and ref_row['total_referrals'] >= ref_count:
            if not await is_user_premium(referrer['user_id']):
                await grant_premium(referrer['user_id'], ref_days, "referral")

    await db.commit()
    return dict(referrer)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Bypass History
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def save_bypass_history(
    user_id: int,
    original_url: str,
    shortener: str,
    destination_url: str,
    final_url: str,
    method: str,
    time_taken: float,
    layer: int = 0,
    success: bool = True,
    error_message: str = None,
    injected_url: str = None,
    shortener_used: str = None
):
    """Save a bypass attempt to history."""
    db = await get_db()
    await db.execute(
        """INSERT INTO bypass_history
           (user_id, original_url, shortener, destination_url, final_url,
            method, layer, time_taken, success, error_message,
            injected_url, shortener_used_for_inject)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (user_id, original_url, shortener, destination_url, final_url,
         method, layer, time_taken, 1 if success else 0, error_message,
         injected_url, shortener_used)
    )
    await db.commit()


async def get_user_history(user_id: int, limit: int = 15) -> List[dict]:
    """Get a user's bypass history."""
    db = await get_db()
    cur = await db.execute(
        "SELECT * FROM bypass_history WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)
    )
    return [dict(r) for r in await cur.fetchall()]


async def get_bypass_stats() -> dict:
    """Get global bypass statistics."""
    db = await get_db()
    total = (await (await db.execute("SELECT COUNT(*) FROM bypass_history")).fetchone())[0]
    successful = (await (await db.execute("SELECT COUNT(*) FROM bypass_history WHERE success=1")).fetchone())[0]
    failed = (await (await db.execute("SELECT COUNT(*) FROM bypass_history WHERE success=0")).fetchone())[0]

    today = datetime.date.today().isoformat()
    today_total = (await (await db.execute(
        "SELECT COUNT(*) FROM bypass_history WHERE date(created_at)=?", (today,)
    )).fetchone())[0]

    # By method
    methods = await (await db.execute(
        "SELECT method, COUNT(*) as cnt FROM bypass_history WHERE success=1 GROUP BY method ORDER BY cnt DESC"
    )).fetchall()

    # Top shorteners
    top_shorteners = await (await db.execute(
        "SELECT shortener, COUNT(*) as cnt FROM bypass_history GROUP BY shortener ORDER BY cnt DESC LIMIT 15"
    )).fetchall()

    # By layer
    layers = await (await db.execute(
        "SELECT layer, COUNT(*) as cnt FROM bypass_history WHERE success=1 GROUP BY layer ORDER BY layer"
    )).fetchall()

    return {
        'total': total,
        'successful': successful,
        'failed': failed,
        'today': today_total,
        'success_rate': round(successful / max(total, 1) * 100, 1),
        'methods': [dict(m) for m in methods],
        'top_shorteners': [dict(s) for s in top_shorteners],
        'layers': [dict(l) for l in layers],
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Shortener Configs (Admin Monetization)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def get_active_shortener_configs() -> List[dict]:
    """Get all active shortener configs ordered by priority."""
    db = await get_db()
    cur = await db.execute(
        "SELECT * FROM shortener_configs WHERE is_active=1 ORDER BY priority ASC"
    )
    return [dict(r) for r in await cur.fetchall()]


async def get_all_shortener_configs() -> List[dict]:
    """Get all shortener configs."""
    db = await get_db()
    cur = await db.execute("SELECT * FROM shortener_configs ORDER BY priority ASC")
    return [dict(r) for r in await cur.fetchall()]


async def upsert_shortener_config(
    shortener_name: str, display_name: str, api_key: str,
    api_endpoint: str, api_format: str = 'json_shortenedUrl',
    priority: int = 5
):
    """Insert or update a shortener config."""
    db = await get_db()
    await db.execute(
        """INSERT OR REPLACE INTO shortener_configs
           (shortener_name, display_name, api_key, api_endpoint, api_format, is_active, total_links_created, priority)
           VALUES (?,?,?,?,?,1,0,?)""",
        (shortener_name, display_name, api_key, api_endpoint, api_format, priority)
    )
    await db.commit()


async def toggle_shortener_config(config_id: int) -> bool:
    """Toggle a shortener config's active status. Returns new state."""
    db = await get_db()
    cur = await db.execute("SELECT is_active FROM shortener_configs WHERE id=?", (config_id,))
    row = await cur.fetchone()
    if not row:
        return False
    new_state = 0 if row['is_active'] else 1
    await db.execute("UPDATE shortener_configs SET is_active=? WHERE id=?", (new_state, config_id))
    await db.commit()
    return bool(new_state)


async def delete_shortener_config(config_id: int):
    """Delete a shortener config."""
    db = await get_db()
    await db.execute("DELETE FROM shortener_configs WHERE id=?", (config_id,))
    await db.commit()


async def increment_shortener_links(config_id: int):
    """Increment the link counter for a shortener config."""
    db = await get_db()
    await db.execute(
        "UPDATE shortener_configs SET total_links_created=total_links_created+1 WHERE id=?",
        (config_id,)
    )
    await db.commit()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Shortener Stats (Bypass Engine Stats)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def update_shortener_stats(shortener: str, success: bool, time_ms: float = 0, error: str = None):
    """Update bypass statistics for a shortener domain."""
    db = await get_db()
    now = datetime.datetime.now().isoformat()
    if success:
        await db.execute(
            """INSERT INTO shortener_stats (shortener, total_bypasses, successful, failed, avg_time_ms, last_success)
               VALUES (?, 1, 1, 0, ?, ?)
               ON CONFLICT(shortener) DO UPDATE SET
               total_bypasses=total_bypasses+1, successful=successful+1,
               avg_time_ms=round((avg_time_ms * successful + ?) / (successful + 1), 1),
               last_success=?""",
            (shortener, time_ms, now, time_ms, now)
        )
    else:
        await db.execute(
            """INSERT INTO shortener_stats (shortener, total_bypasses, successful, failed, last_failure, last_error)
               VALUES (?, 1, 0, 1, ?, ?)
               ON CONFLICT(shortener) DO UPDATE SET
               total_bypasses=total_bypasses+1, failed=failed+1,
               last_failure=?, last_error=?""",
            (shortener, now, error, now, error)
        )
    await db.commit()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Bypass Cache
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def get_cached_bypass(url: str) -> Optional[dict]:
    """Check if a bypass result is cached and still valid."""
    cache_enabled = await get_setting('cache_enabled', 'true')
    if cache_enabled != 'true':
        return None
    db = await get_db()
    cur = await db.execute(
        "SELECT * FROM bypass_cache WHERE original_url=? AND expires_at > datetime('now')",
        (url,)
    )
    row = await cur.fetchone()
    if row:
        await db.execute(
            "UPDATE bypass_cache SET hit_count=hit_count+1 WHERE original_url=?", (url,)
        )
        await db.commit()
        return dict(row)
    return None


async def set_cached_bypass(url: str, destination: str, method: str, shortener: str = 'unknown'):
    """Cache a bypass result."""
    cache_enabled = await get_setting('cache_enabled', 'true')
    if cache_enabled != 'true':
        return
    ttl_hours = int(await get_setting('cache_ttl_hours', '24'))
    db = await get_db()
    await db.execute(
        """INSERT OR REPLACE INTO bypass_cache
           (original_url, destination_url, method, shortener, created_at, expires_at, hit_count)
           VALUES (?, ?, ?, ?, datetime('now'), datetime('now', ?||' hours'), 0)""",
        (url, destination, method, shortener, str(ttl_hours))
    )
    await db.commit()


async def clean_expired_cache():
    """Remove expired cache entries."""
    db = await get_db()
    result = await db.execute("DELETE FROM bypass_cache WHERE expires_at < datetime('now')")
    await db.commit()
    return result.rowcount


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API Usage Tracking
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def log_api_usage(api_name: str, endpoint: str, status_code: int,
                        response_time_ms: float, success: bool, error: str = None):
    """Log an external API call for monitoring."""
    db = await get_db()
    await db.execute(
        """INSERT INTO api_usage (api_name, endpoint, status_code, response_time_ms, success, error_message)
           VALUES (?,?,?,?,?,?)""",
        (api_name, endpoint, status_code, response_time_ms, 1 if success else 0, error)
    )
    await db.commit()


async def get_api_stats(hours: int = 24) -> List[dict]:
    """Get API usage stats for the last N hours."""
    db = await get_db()
    cur = await db.execute(
        """SELECT api_name,
                  COUNT(*) as total_calls,
                  SUM(CASE WHEN success=1 THEN 1 ELSE 0 END) as successful,
                  ROUND(AVG(response_time_ms), 1) as avg_time_ms,
                  ROUND(SUM(CASE WHEN success=1 THEN 1.0 ELSE 0 END) / COUNT(*) * 100, 1) as success_rate
           FROM api_usage
           WHERE created_at > datetime('now', ?||' hours')
           GROUP BY api_name
           ORDER BY total_calls DESC""",
        (str(-hours),)
    )
    return [dict(r) for r in await cur.fetchall()]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Analytics
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def update_daily_analytics():
    """Update today's analytics snapshot."""
    db = await get_db()
    today = datetime.date.today().isoformat()

    total_users = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
    new_users = (await (await db.execute(
        "SELECT COUNT(*) FROM users WHERE date(created_at)=?", (today,)
    )).fetchone())[0]
    active_users = (await (await db.execute(
        "SELECT COUNT(*) FROM users WHERE date(last_active)=?", (today,)
    )).fetchone())[0]
    total_bypasses = (await (await db.execute(
        "SELECT COUNT(*) FROM bypass_history WHERE date(created_at)=?", (today,)
    )).fetchone())[0]
    successful = (await (await db.execute(
        "SELECT COUNT(*) FROM bypass_history WHERE date(created_at)=? AND success=1", (today,)
    )).fetchone())[0]
    failed = total_bypasses - successful
    injected = (await (await db.execute(
        "SELECT COUNT(*) FROM bypass_history WHERE date(created_at)=? AND injected_url IS NOT NULL", (today,)
    )).fetchone())[0]

    await db.execute(
        """INSERT OR REPLACE INTO analytics_daily
           (date, total_users, new_users, active_users, total_bypasses,
            successful_bypasses, failed_bypasses, total_injected_links)
           VALUES (?,?,?,?,?,?,?,?)""",
        (today, total_users, new_users, active_users, total_bypasses, successful, failed, injected)
    )
    await db.commit()


async def get_analytics_range(days: int = 7) -> List[dict]:
    """Get analytics for the last N days."""
    db = await get_db()
    cur = await db.execute(
        """SELECT * FROM analytics_daily
           WHERE date >= date('now', ?||' days')
           ORDER BY date DESC""",
        (str(-days),)
    )
    return [dict(r) for r in await cur.fetchall()]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Force Subscribe
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def get_force_sub_channels() -> List[dict]:
    """Get all active force-subscribe channels."""
    db = await get_db()
    cur = await db.execute("SELECT * FROM force_sub_channels WHERE is_active=1")
    return [dict(r) for r in await cur.fetchall()]


async def add_force_sub_channel(username: str, channel_id: int = None, title: str = None):
    """Add a force-subscribe channel."""
    db = await get_db()
    await db.execute(
        "INSERT OR IGNORE INTO force_sub_channels (channel_username, channel_id, channel_title) VALUES (?,?,?)",
        (username, channel_id, title)
    )
    await db.commit()


async def remove_force_sub_channel(channel_id: int):
    """Remove a force-subscribe channel."""
    db = await get_db()
    await db.execute("DELETE FROM force_sub_channels WHERE id=?", (channel_id,))
    await db.commit()

import aiosqlite, secrets, time as _time
from bot.config import DB_PATH

_db = None

async def get_db():
    global _db
    if _db is None:
        _db = await aiosqlite.connect(DB_PATH)
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
    return _db

async def init_db():
    db = await get_db()
    await db.executescript(\"\"\"
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT,
        language TEXT DEFAULT 'en', is_premium INTEGER DEFAULT 0,
        premium_until TIMESTAMP NULL, premium_source TEXT NULL,
        daily_bypasses_used INTEGER DEFAULT 0, total_bypasses INTEGER DEFAULT 0,
        bonus_credits INTEGER DEFAULT 0, referred_by INTEGER NULL,
        referral_code TEXT UNIQUE NOT NULL, total_referrals INTEGER DEFAULT 0,
        referral_premium_until TIMESTAMP NULL, is_banned INTEGER DEFAULT 0,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS bypass_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
        original_url TEXT NOT NULL, shortener_detected TEXT NOT NULL,
        destination_url TEXT NOT NULL, injected_url TEXT NULL,
        bypass_method TEXT NOT NULL, bypass_time_ms INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS shortener_configs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, shortener_name TEXT UNIQUE NOT NULL,
        display_name TEXT NOT NULL, api_key TEXT NOT NULL, api_endpoint TEXT NOT NULL,
        api_format TEXT NOT NULL, is_active INTEGER DEFAULT 1,
        total_links_created INTEGER DEFAULT 0, priority INTEGER DEFAULT 5,
        last_tested TIMESTAMP NULL, last_test_result TEXT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS force_sub_channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT, channel_username TEXT UNIQUE NOT NULL,
        channel_id INTEGER NULL, is_active INTEGER DEFAULT 1,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS analytics_daily (
        id INTEGER PRIMARY KEY AUTOINCREMENT, date DATE UNIQUE NOT NULL,
        total_users INTEGER DEFAULT 0, new_users INTEGER DEFAULT 0,
        total_bypasses INTEGER DEFAULT 0, total_injected_links INTEGER DEFAULT 0,
        premium_purchases INTEGER DEFAULT 0, referral_signups INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS supported_shorteners (
        id INTEGER PRIMARY KEY AUTOINCREMENT, domain TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL, bypass_method TEXT NOT NULL,
        pattern_module TEXT NULL, is_working INTEGER DEFAULT 1,
        success_count INTEGER DEFAULT 0, fail_count INTEGER DEFAULT 0,
        last_tested TIMESTAMP NULL
    );
    CREATE TABLE IF NOT EXISTS broadcast_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT, message_text TEXT NOT NULL,
        message_type TEXT DEFAULT 'text', media_file_id TEXT NULL,
        total_target INTEGER DEFAULT 0, sent_count INTEGER DEFAULT 0,
        failed_count INTEGER DEFAULT 0, status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY, value TEXT NOT NULL, description TEXT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    \"\"\")
    defaults = {
        "bot_name": "LinkBypass Pro",
        "welcome_message": "\U0001f513 Welcome to LinkBypass Pro!\n\nI bypass 500+ link shorteners instantly!\n\nJust send me any shortened link! \U0001f680",
        "bypass_success_message": "\u2705 Link Bypassed Successfully!",
        "default_language": "en", "free_daily_limit": "5", "cooldown_seconds": "10",
        "batch_limit_free": "3", "batch_limit_premium": "50",
        "inject_links_enabled": "true", "shortener_rotation_mode": "round_robin",
        "premium_stars_enabled": "true", "premium_stars_price": "50",
        "premium_stars_days": "30", "premium_referral_enabled": "true",
        "premium_referral_count": "3", "premium_referral_days": "3",
        "force_sub_enabled": "false", "antispam_enabled": "true",
        "max_requests_per_minute": "5", "referral_bonus_credits": "5",
    }
    for k, v in defaults.items():
        await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
    await db.commit()

async def get_setting(key):
    db = await get_db()
    cur = await db.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = await cur.fetchone()
    return row[0] if row else None

async def set_setting(key, value):
    db = await get_db()
    await db.execute("INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))", (key, str(value)))
    await db.commit()

async def get_or_create_user(user_id, tg_user=None):
    db = await get_db()
    cur = await db.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = await cur.fetchone()
    if row:
        if tg_user:
            await db.execute("UPDATE users SET username=?, full_name=?, last_active=datetime('now') WHERE user_id=?",
                (tg_user.username or "", tg_user.full_name or "", user_id))
            await db.commit()
        return dict(row)
    code = secrets.token_hex(4)
    name = tg_user.full_name if tg_user else ""
    uname = tg_user.username if tg_user else ""
    await db.execute("INSERT INTO users (user_id, username, full_name, referral_code) VALUES (?,?,?,?)",
        (user_id, uname or "", name or "", code))
    await db.commit()
    cur = await db.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    return dict(await cur.fetchone())

async def increment_daily_bypass(user_id):
    db = await get_db()
    await db.execute("UPDATE users SET daily_bypasses_used=daily_bypasses_used+1, total_bypasses=total_bypasses+1 WHERE user_id=?", (user_id,))
    await db.commit()

async def save_bypass_history(user_id, original_url, shortener, destination, injected_url, method, time_ms):
    db = await get_db()
    await db.execute("INSERT INTO bypass_history (user_id, original_url, shortener_detected, destination_url, injected_url, bypass_method, bypass_time_ms) VALUES (?,?,?,?,?,?,?)",
        (user_id, original_url, shortener, destination, injected_url, method, time_ms))
    await db.commit()

async def get_active_shortener_configs():
    db = await get_db()
    cur = await db.execute("SELECT * FROM shortener_configs WHERE is_active=1 ORDER BY priority ASC")
    return [dict(r) for r in await cur.fetchall()]

async def get_user_count():
    db = await get_db()
    cur = await db.execute("SELECT COUNT(*) FROM users")
    return (await cur.fetchone())[0]

async def get_all_user_ids():
    db = await get_db()
    cur = await db.execute("SELECT user_id FROM users WHERE is_banned=0")
    return [r[0] for r in await cur.fetchall()]

async def reset_daily_bypasses():
    db = await get_db()
    await db.execute("UPDATE users SET daily_bypasses_used=0")
    await db.commit()

async def increment_shortener_links(config_id):
    db = await get_db()
    await db.execute("UPDATE shortener_configs SET total_links_created=total_links_created+1 WHERE id=?", (config_id,))
    await db.commit()

async def update_shortener_stats(domain, success=True):
    db = await get_db()
    if success:
        await db.execute("UPDATE supported_shorteners SET success_count=success_count+1 WHERE domain=?", (domain,))
    else:
        await db.execute("UPDATE supported_shorteners SET fail_count=fail_count+1 WHERE domain=?", (domain,))
    await db.commit()

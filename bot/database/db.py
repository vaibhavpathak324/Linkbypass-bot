import aiosqlite, secrets, time as _time
from bot.config import DB_PATH

_db = None

async def get_db():
    global _db
    if _db is None:
        _db = await aiosqlite.connect(DB_PATH)
        _db.row_factory = aiosqlite.Row
        await init_db()
    return _db

async def init_db():
    db = await get_db()
    await db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT,
        language TEXT DEFAULT 'en', is_premium INTEGER DEFAULT 0,
        premium_until TIMESTAMP NULL, premium_source TEXT NULL,
        daily_bypasses INTEGER DEFAULT 0, total_bypasses INTEGER DEFAULT 0,
        referral_code TEXT UNIQUE, referred_by INTEGER NULL,
        referral_count INTEGER DEFAULT 0, bonus_bypasses INTEGER DEFAULT 0,
        last_bypass REAL DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS bypass_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
        original_url TEXT, bypassed_url TEXT, shortener TEXT,
        method TEXT, time_taken REAL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS shorteners (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
        api_key TEXT NOT NULL, api_url TEXT NOT NULL,
        is_active INTEGER DEFAULT 0, intercept_percent INTEGER DEFAULT 30,
        total_links INTEGER DEFAULT 0,
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
        total_bypasses INTEGER DEFAULT 0, total_intercepted_links INTEGER DEFAULT 0,
        premium_purchases INTEGER DEFAULT 0, signup_signoups INTEGER DEFAULT 0
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
    CREATE TABLE IF NOT EXISTS shortener_stats (
        shortener TEXT PRIMARY KEY, total_bypasses INTEGER DEFAULT 0,
        successful INTEGER DEFAULT 0, failed INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS ad_config (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ad_text TEXT NOT NULL,
        ad_url TEXT NOT NULL, is_active INTEGER DEFAULT 1,
        show_every_n INTEGER DEFAULT 5
    );
    """)

    # Default settings
    defaults = {
        'daily_limit': '15', 'cooldown_seconds': '5',
        'bonus_per_referred': '0', 'intercept_links_enabled': '0',
        'welcome_message': '', 'maintenance_mode': '0',
        'ads_enabled': '0', 'premium_price_stars': '150',
        'premium_days': '30', 'signup_bonus': '5',
        'signup_enabled': '1'
    }
    for k, v in defaults.items():
        await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
    await db.commit()

async def get_setting(key, default=None):
    db = await get_db()
    cur = await db.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = await cur.fetchone()
    return row['value'] if row else default

async def set_setting(key, value):
    db = await get_db()
    await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    await db.commit()

async def get_or_create_user(user_id, username=None, full_name=None):
    db = await get_db()
    cur = await db.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = await cur.fetchone()
    if not user:
        ref_code = secrets.token_hex(4)
        await db.execute(
            "INSERT INTO users (user_id, username, full_name, referral_code) VALUES (?, ?, ?, ?)",
            (user_id, username, full_name, ref_code))
        await db.commit()
        cur = await db.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        user = await cur.fetchone()
    return dict(user)

async def increment_daily_bypasses(user_id):
    db = await get_db()
    await db.execute("UPDATE users SET daily_bypasses=daily_bypasses+1, total_bypasses=total_bypasses+1 WHERE user_id=?", (user_id,))
    await db.commit()

async def reset_daily_bypasses():
    db = await get_db()
    await db.execute("UPDATE users SET daily_bypasses=0")
    await db.commit()

async def save_bypass_history(user_id, original, bypassed, shortener, method, time_taken):
    db = await get_db()
    await db.execute(
        "INSERT INTO bypass_history (user_id, original_url, bypassed_url, shortener, method, time_taken) VALUES (?,?,?,?,?,?)",
        (user_id, original, bypassed, shortener, method, time_taken))
    await db.commit()

async def get_user_count():
    db = await get_db()
    cur = await db.execute("SELECT COUNT(*) as cnt FROM users")
    row = await cur.fetchone()
    return row['cnt']

async def get_active_shorteners_db():
    db = await get_db()
    cur = await db.execute("SELECT * FROM shorteners WHERE is_active=1")
    return [dict(r) for r in await cur.fetchall()]

async def increment_shortener_links(shortener_id):
    db = await get_db()
    await db.execute("UPDATE shorteners SET total_links=total_links+1 WHERE id=?", (shortener_id,))
    await db.commit()

async def update_shortener_stats(shortener, success):
    db = await get_db()
    await db.execute(
        "INSERT INTO shortener_stats (shortener, total_bypasses, successful, failed) VALUES (?, 1, ?, ?) "
        "ON CONFLICT(shortener) DO UPDATE SET total_bypasses=total_bypasses+1, "
        "successful=successful+?, failed=failed+?",
        (shortener, 1 if success else 0, 0 if success else 1, 1 if success else 0, 0 if success else 1))
    await db.commit()

async def get_all_user_ids():
    db = await get_db()
    cur = await db.execute("SELECT user_id FROM users")
    return [row['user_id'] for row in await cur.fetchall()]
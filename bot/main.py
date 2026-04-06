import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from bot.config import BOT_TOKEN, ADMIN_USER_ID, PORT
from bot.database.db import init_db, get_db, reset_daily_bypasses, get_user_count
from bot.engine.domain_list import KNOWN_SHORTENER_DOMAINS

from bot.handlers.start import router as start_router
from bot.handlers.bypass import router as bypass_router
from bot.handlers.help_cmd import router as help_router
from bot.handlers.premium import router as premium_router
from bot.handlers.referral import router as referral_router
from bot.handlers.history import router as history_router
from bot.handlers.batch import router as batch_router
from bot.handlers.language import router as language_router
from bot.handlers.check import router as check_router
from bot.handlers.admin.panel import router as admin_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def health_handler(request):
    count = await get_user_count()
    return web.json_response({"status": "ok", "users": count, "shorteners": len(KNOWN_SHORTENER_DOMAINS)})

async def start_health_server():
    app = web.Application()
    app.router.add_get("/", health_handler)
    app.router.add_get("/health", health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Health server on port {PORT}")

async def daily_reset_task():
    while True:
        await asyncio.sleep(86400)
        try:
            await reset_daily_bypasses()
            logger.info("Daily bypasses reset")
        except Exception as e:
            logger.error(f"Reset error: {e}")

async def premium_check_task(bot: Bot):
    while True:
        await asyncio.sleep(3600)
        try:
            db = await get_db()
            cur = await db.execute("SELECT user_id FROM users WHERE is_premium=1 AND premium_until < datetime('now')")
            expired = await cur.fetchall()
            for row in expired:
                uid = row[0]
                await db.execute("UPDATE users SET is_premium=0 WHERE user_id=?", (uid,))
                try:
                    await bot.send_message(uid, "\u2b50 Your premium has expired. Renew: /premium")
                except:
                    pass
            await db.commit()
        except Exception as e:
            logger.error(f"Premium check error: {e}")

async def seed_shorteners():
    db = await get_db()
    for domain, name in KNOWN_SHORTENER_DOMAINS.items():
        await db.execute(
            "INSERT OR IGNORE INTO supported_shorteners (domain, name, bypass_method) VALUES (?, ?, 'auto')",
            (domain, name))
    await db.commit()
    logger.info(f"Seeded {len(KNOWN_SHORTENER_DOMAINS)} shortener domains")

async def main():
    await init_db()
    await seed_shorteners()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(admin_router)
    dp.include_router(start_router)
    dp.include_router(help_router)
    dp.include_router(premium_router)
    dp.include_router(referral_router)
    dp.include_router(history_router)
    dp.include_router(batch_router)
    dp.include_router(language_router)
    dp.include_router(check_router)
    dp.include_router(bypass_router)

    await bot.set_my_commands([
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="help", description="How to use"),
        BotCommand(command="batch", description="Bypass multiple links"),
        BotCommand(command="history", description="Your bypass history"),
        BotCommand(command="supported", description="Supported shorteners"),
        BotCommand(command="premium", description="Get unlimited bypasses"),
        BotCommand(command="referral", description="Invite friends"),
        BotCommand(command="language", description="Change language"),
        BotCommand(command="admin", description="Admin panel"),
    ])

    await start_health_server()
    asyncio.create_task(daily_reset_task())
    asyncio.create_task(premium_check_task(bot))

    logger.info("LinkBypass Pro Bot started!")
    try:
        await bot.send_message(ADMIN_USER_ID, "\ud83e\udd16 LinkBypass Pro Bot started!\n\nUse /admin to access the admin panel.")
    except:
        pass

    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())

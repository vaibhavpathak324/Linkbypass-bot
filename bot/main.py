"""
LinkBypass Pro — Main Entry Point
====================================
Initializes the bot, registers all handlers, starts the
web server for health checks, and runs the polling loop.
"""

import os
import sys
import asyncio
import logging
import signal
from datetime import datetime, time as dt_time

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from bot.config import BOT_TOKEN, WEB_HOST, WEB_PORT, BOT_NAME, BOT_VERSION, logger
from bot.database.db import get_db, close_db, reset_daily_bypasses, clean_expired_cache, get_user_count
from bot.engine.domain_list import get_total_count


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Web Server (Health Check for Render)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def health_handler(request):
    """Health check endpoint."""
    try:
        user_count = await get_user_count()
    except Exception:
        user_count = 0

    return web.json_response({
        "status": "ok",
        "bot": BOT_NAME,
        "version": BOT_VERSION,
        "users": user_count,
        "shorteners": get_total_count(),
        "timestamp": datetime.utcnow().isoformat(),
    })


async def root_handler(request):
    """Root endpoint."""
    return web.json_response({
        "name": BOT_NAME,
        "version": BOT_VERSION,
        "status": "running",
        "docs": "Send /start to the Telegram bot to get started.",
    })


async def start_web_server():
    """Start the aiohttp web server for health checks."""
    app = web.Application()
    app.router.add_get('/health', health_handler)
    app.router.add_get('/', root_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, WEB_HOST, WEB_PORT)
    await site.start()
    logger.info(f"Web server started on {WEB_HOST}:{WEB_PORT}")
    return runner


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Background Tasks
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def daily_reset_task():
    """Reset daily bypass counters at midnight UTC."""
    while True:
        now = datetime.utcnow()
        tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if tomorrow <= now:
            tomorrow = tomorrow.replace(day=tomorrow.day + 1)
        wait_seconds = (tomorrow - now).total_seconds()

        logger.info(f"Daily reset scheduled in {wait_seconds:.0f}s")
        await asyncio.sleep(wait_seconds)

        try:
            await reset_daily_bypasses()
            await clean_expired_cache()
            logger.info("Daily reset completed: bypasses reset, cache cleaned")
        except Exception as e:
            logger.error(f"Daily reset error: {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Bot Setup
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def main():
    """Main function — initializes and starts the bot."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set! Set the BOT_TOKEN environment variable.")
        sys.exit(1)

    # Initialize database
    await get_db()
    logger.info("Database initialized")

    # Create bot and dispatcher
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=None)
    )
    dp = Dispatcher()

    # Register all handlers
    from bot.handlers.start import router as start_router
    from bot.handlers.bypass import router as bypass_router
    from bot.handlers.batch import router as batch_router
    from bot.handlers.history import router as history_router
    from bot.handlers.premium import router as premium_router
    from bot.handlers.referral import router as referral_router
    from bot.handlers.help_cmd import router as help_router
    from bot.handlers.check import router as check_router
    from bot.handlers.language import router as language_router
    from bot.handlers.admin.panel import router as admin_router

    dp.include_router(admin_router)    # Admin first (high priority)
    dp.include_router(start_router)
    dp.include_router(premium_router)
    dp.include_router(help_router)
    dp.include_router(check_router)
    dp.include_router(language_router)
    dp.include_router(history_router)
    dp.include_router(referral_router)
    dp.include_router(batch_router)
    dp.include_router(bypass_router)    # Bypass last (catch-all for URLs)

    # Start web server
    web_runner = await start_web_server()

    # Start background tasks
    reset_task = asyncio.create_task(daily_reset_task())

    logger.info(f"🚀 {BOT_NAME} v{BOT_VERSION} starting...")
    logger.info(f"📊 {get_total_count()}+ shorteners supported")

    try:
        # Delete webhook to ensure polling works
        await bot.delete_webhook(drop_pending_updates=True)

        # Start polling
        await dp.start_polling(bot)
    finally:
        # Cleanup
        reset_task.cancel()
        await close_db()
        await web_runner.cleanup()
        logger.info("Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot shutdown requested")

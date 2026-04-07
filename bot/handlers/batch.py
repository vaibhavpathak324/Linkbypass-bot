"""
LinkBypass Pro — Batch Bypass Handler
=======================================
Handles multiple URL bypass in a single message.
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot.database.db import (
    get_or_create_user, get_setting, is_user_premium,
    increment_daily_bypass, save_bypass_history
)
from bot.engine.manager import bypass_urls
from bot.engine.url_utils import extract_urls, truncate, format_time_ms
from bot.injection.injector import link_injector

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "help_batch")
async def help_batch(callback: CallbackQuery):
    """Show batch bypass help."""
    text = (
        "📦 Batch Bypass\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Send multiple links in one message to bypass them all at once!\n\n"
        "📌 Just paste multiple URLs (one per line):\n"
        "https://shrinkme.io/XXXX\n"
        "https://gplinks.co/YYYY\n"
        "https://ouo.io/ZZZZ\n\n"
        "Use /batch command for explicit batch mode."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="back_start")]
    ])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

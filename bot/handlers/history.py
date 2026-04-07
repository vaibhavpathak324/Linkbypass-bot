"""
LinkBypass Pro — History Handler
==================================
Shows user's bypass history.
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from bot.database.db import get_user_history
from bot.engine.url_utils import truncate, format_time_ms

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("history"))
async def cmd_history(message: Message):
    """Show bypass history."""
    await _show_history(message, message.from_user.id)


@router.callback_query(F.data == "show_history")
async def cb_history(callback: CallbackQuery):
    """Show bypass history via callback."""
    await _show_history_edit(callback, callback.from_user.id)
    await callback.answer()


async def _show_history(message: Message, user_id: int):
    """Send history as new message."""
    history = await get_user_history(user_id, limit=15)

    if not history:
        await message.answer(
            "📋 No bypass history yet.\n\nSend me a shortened link to get started!"
        )
        return

    text = "📋 Your Bypass History (last 15):\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, r in enumerate(history, 1):
        status = "✅" if r['success'] else "❌"
        text += (
            f"{i}. {status} {truncate(r['original_url'], 35)}\n"
            f"   → {truncate(r['destination_url'] or 'N/A', 35)}\n"
            f"   ⏱ {format_time_ms(r['time_taken'])} | 🏷 {r['shortener']} | ⚙️ {r['method']}\n\n"
        )

    await message.answer(text)


async def _show_history_edit(callback: CallbackQuery, user_id: int):
    """Show history by editing message."""
    history = await get_user_history(user_id, limit=10)

    if not history:
        text = "📋 No bypass history yet.\n\nSend me a shortened link to get started!"
    else:
        text = "📋 Recent Bypass History:\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        for i, r in enumerate(history, 1):
            status = "✅" if r['success'] else "❌"
            text += (
                f"{i}. {status} {truncate(r['original_url'], 30)} → "
                f"{truncate(r['destination_url'] or 'N/A', 30)}\n"
                f"   {format_time_ms(r['time_taken'])} | {r['shortener']}\n\n"
            )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="back_start")]
    ])
    await callback.message.edit_text(text, reply_markup=kb)

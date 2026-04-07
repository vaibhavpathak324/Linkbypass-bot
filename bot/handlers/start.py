"""
LinkBypass Pro — /start Handler
=================================
Handles the /start command with referral processing,
welcome message, and force-subscribe checking.
"""

import logging
from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart, CommandObject

from bot.config import BOT_NAME, BOT_VERSION, ADMIN_USER_ID
from bot.database.db import (
    get_or_create_user, process_referral, get_setting,
    get_user_count, is_user_premium
)
from bot.engine.domain_list import get_total_count
from bot.services.force_sub_service import check_force_sub

logger = logging.getLogger(__name__)
router = Router()


def _main_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Generate the main menu keyboard."""
    buttons = [
        [InlineKeyboardButton(text="🔓 Bypass Link", callback_data="help_bypass"),
         InlineKeyboardButton(text="📦 Batch Bypass", callback_data="help_batch")],
        [InlineKeyboardButton(text="📋 History", callback_data="show_history"),
         InlineKeyboardButton(text="⭐ Premium", callback_data="show_premium")],
        [InlineKeyboardButton(text="👥 Referral", callback_data="show_referral"),
         InlineKeyboardButton(text="🌐 Language", callback_data="show_language")],
        [InlineKeyboardButton(text="ℹ️ Help", callback_data="show_help"),
         InlineKeyboardButton(text="📊 Stats", callback_data="show_stats")],
    ]
    if user_id == ADMIN_USER_ID:
        buttons.append([InlineKeyboardButton(text="🔧 Admin Panel", callback_data="admin_menu")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject = None):
    """Handle /start with optional referral code."""
    user = await get_or_create_user(message.from_user.id, message.from_user)

    # Check force subscribe
    fsub_ok = await check_force_sub(message.bot, message.from_user.id)
    if not fsub_ok:
        return  # Force sub handler will send the message

    # Process referral if present
    if command and command.args:
        args = command.args
        if args.startswith('ref_'):
            ref_code = args[4:]
            referrer = await process_referral(message.from_user.id, ref_code)
            if referrer:
                await message.answer(
                    f"🎉 You were referred by a friend! Both of you get bonus credits."
                )

    # Welcome message
    is_prem = await is_user_premium(message.from_user.id)
    total_shorteners = get_total_count()
    daily_limit = int(await get_setting(
        'premium_daily_limit' if is_prem else 'free_daily_limit', '15'
    ))

    custom_welcome = await get_setting('welcome_message', '')
    if custom_welcome:
        welcome = custom_welcome
    else:
        welcome = (
            f"👋 Welcome to {BOT_NAME}!\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔓 I can bypass {total_shorteners}+ URL shorteners instantly!\n\n"
            f"Just send me any shortened link and I'll extract the real destination.\n\n"
            f"{'⭐ Premium Member' if is_prem else '👤 Free Plan'} • "
            f"{daily_limit} bypasses/day\n\n"
            f"📌 Supported: GPLinks, ShrinkMe, OUO, Linkvertise, Ad.fly, "
            f"Droplink, ShareUs, and {total_shorteners - 7}+ more!"
        )

    await message.answer(
        welcome,
        reply_markup=_main_keyboard(message.from_user.id)
    )


@router.callback_query(F.data == "back_start")
async def back_to_start(callback: CallbackQuery):
    """Go back to start menu."""
    user = await get_or_create_user(callback.from_user.id, callback.from_user)
    is_prem = await is_user_premium(callback.from_user.id)
    total_shorteners = get_total_count()

    text = (
        f"👋 {BOT_NAME} — Main Menu\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔓 Send me any short link to bypass it!\n\n"
        f"{'⭐ Premium' if is_prem else '👤 Free'} • "
        f"{total_shorteners}+ shorteners supported"
    )

    await callback.message.edit_text(
        text,
        reply_markup=_main_keyboard(callback.from_user.id)
    )
    await callback.answer()


@router.callback_query(F.data == "show_stats")
async def show_stats(callback: CallbackQuery):
    """Show bot statistics."""
    user_count = await get_user_count()
    total_shorteners = get_total_count()

    from bot.database.db import get_bypass_stats
    stats = await get_bypass_stats()

    text = (
        f"📊 Bot Statistics\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Total Users: {user_count}\n"
        f"🔗 Shorteners Supported: {total_shorteners}+\n\n"
        f"🔓 Bypass Stats:\n"
        f"├── Total: {stats['total']}\n"
        f"├── Today: {stats['today']}\n"
        f"├── Success Rate: {stats['success_rate']}%\n"
        f"└── Successful: {stats['successful']}\n\n"
        f"🏗 Version: {BOT_VERSION}"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="back_start")]
    ])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

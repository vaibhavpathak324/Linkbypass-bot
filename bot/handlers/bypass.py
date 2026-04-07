"""
LinkBypass Pro — Bypass Handler
====================================
Handles incoming URLs from users and processes
through the bypass engine.
"""

import time
import logging
from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot.config import ADMIN_USER_ID
from bot.database.db import (
    get_or_create_user, get_setting, increment_daily_bypass,
    save_bypass_history, is_user_premium, update_user
)
from bot.engine.manager import bypass_url, BypassResult
from bot.engine.url_utils import (
    extract_urls, is_valid_url, is_shortener_url,
    detect_shortener, truncate, format_time_ms
)
from bot.injection.injector import link_injector

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text.regexp(r'https?://'))
async def handle_link(message: Message):
    """Handle any message containing a URL."""
    user = await get_or_create_user(message.from_user.id, message.from_user)

    # Check if banned
    if user.get('is_banned'):
        await message.answer("❌ Your account has been banned. Contact admin for help.")
        return

    # Check maintenance mode
    maintenance = await get_setting('maintenance_mode', 'false')
    if maintenance == 'true' and message.from_user.id != ADMIN_USER_ID:
        msg = await get_setting('maintenance_message', 'Bot is under maintenance.')
        await message.answer(f"🔧 {msg}")
        return

    # Extract URLs
    urls = extract_urls(message.text)
    if not urls:
        await message.answer("❌ No valid URL found in your message.")
        return

    url = urls[0]  # Process first URL

    # Check daily limit
    is_prem = await is_user_premium(message.from_user.id)
    limit_key = 'premium_daily_limit' if is_prem else 'free_daily_limit'
    daily_limit = int(await get_setting(limit_key, '15'))

    if user['daily_bypasses_used'] >= daily_limit:
        if not is_prem:
            await message.answer(
                f"⚠️ Daily limit reached ({daily_limit} bypasses)!\n\n"
                f"⭐ Upgrade to Premium for unlimited bypasses:\n"
                f"• /premium — See premium plans",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⭐ Get Premium", callback_data="show_premium")]
                ])
            )
        else:
            await message.answer(f"⚠️ Premium daily limit reached ({daily_limit}).")
        return

    # Check cooldown
    cooldown = int(await get_setting('cooldown_seconds', '5'))
    elapsed = time.time() - user.get('last_bypass', 0)
    if elapsed < cooldown and message.from_user.id != ADMIN_USER_ID:
        remaining = int(cooldown - elapsed)
        await message.answer(f"⏳ Please wait {remaining}s before next bypass.")
        return

    # Detect shortener
    shortener_name, category = detect_shortener(url)

    # Send processing message
    status_msg = await message.answer(
        f"🔄 Bypassing link...\n"
        f"🔗 {truncate(url, 50)}\n"
        f"🏷 Detected: {shortener_name}\n"
        f"⏳ Processing..."
    )

    # Perform bypass
    start = time.time()
    try:
        result = await bypass_url(url)
    except Exception as exc:
        logger.error(f"bypass_url crashed: {exc}", exc_info=True)
        await status_msg.edit_text(
            f"❌ Bypass Error\n\n"
            f"🔗 URL: {truncate(url, 45)}\n"
            f"⚠️ Internal error: {str(exc)[:100]}\n\n"
            f"Please try again later."
        )
        return
    elapsed_ms = (time.time() - start) * 1000

    if result.success:
        # Increment bypass counter
        await increment_daily_bypass(message.from_user.id)

        # Check for link injection (monetization)
        final_url = result.destination_url
        injected_url = None
        shortener_used = None

        inject_enabled = await get_setting('inject_links_enabled', 'false')
        if inject_enabled == 'true' and not is_prem:
            injection = await link_injector.inject(result.destination_url, is_prem)
            if not injection['is_direct']:
                final_url = injection['final_url']
                injected_url = injection['final_url']
                shortener_used = injection['shortener_used']

        # Save to history
        await save_bypass_history(
            user_id=message.from_user.id,
            original_url=url,
            shortener=result.shortener,
            destination_url=result.destination_url,
            final_url=final_url,
            method=result.method,
            time_taken=result.time_taken_ms,
            layer=result.layer,
            success=True,
            injected_url=injected_url,
            shortener_used=shortener_used,
        )

        # Format success message
        cache_badge = "⚡ " if result.cached else ""
        text = (
            f"✅ Link Bypassed Successfully!\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔗 Original: {truncate(url, 45)}\n"
            f"🏷 Shortener: {result.shortener}\n"
            f"⚙️ Method: {result.method} (Layer {result.layer})\n"
            f"⏱ Time: {cache_badge}{format_time_ms(result.time_taken_ms)}\n\n"
            f"🎯 Destination:\n{final_url}"
        )

        remaining = daily_limit - user['daily_bypasses_used'] - 1
        if remaining <= 5 and not is_prem:
            text += f"\n\n⚠️ {remaining} bypasses remaining today"

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Open Link", url=final_url)],
        ])

        await status_msg.edit_text(text, reply_markup=kb, disable_web_page_preview=True)

    else:
        # Save failed attempt
        await save_bypass_history(
            user_id=message.from_user.id,
            original_url=url,
            shortener=result.shortener,
            destination_url="",
            final_url="",
            method=result.method,
            time_taken=result.time_taken_ms,
            success=False,
            error_message=result.error,
        )

        text = (
            f"❌ Bypass Failed\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔗 URL: {truncate(url, 45)}\n"
            f"🏷 Shortener: {result.shortener}\n"
            f"⏱ Tried for: {format_time_ms(result.time_taken_ms)}\n\n"
            f"💡 This shortener may have anti-bot protection.\n"
            f"Try again later or send a different link."
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Retry", callback_data=f"retry_{url[:50]}"),
             InlineKeyboardButton(text="🔙 Menu", callback_data="back_start")]
        ])

        await status_msg.edit_text(text, reply_markup=kb)


@router.callback_query(F.data == "help_bypass")
async def help_bypass(callback: CallbackQuery):
    """Show bypass help."""
    text = (
        "🔓 How to Bypass Links\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Simply send me any shortened URL and I'll extract\n"
        "the real destination link.\n\n"
        "�L Examples:\n"
        "• https://shrinkme.io/XXXX\n"
        "• https://gplinks.co/XXXX\n"
        "• https://ouo.io/XXXX\n"
        "• https://bit.ly/XXXX\n\n"
        "🔗 Just paste the link and hit send!"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="back_start")]
    ])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

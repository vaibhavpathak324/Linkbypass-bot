from aiogram import Router, Bot, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot.database.db import (get_or_create_user, get_setting, increment_daily_bypass,
    save_bypass_history, update_shortener_stats)
from bot.engine.manager import BypassManager
from bot.engine.url_utils import extract_url, truncate
from bot.injection.injector import link_injector
from bot.services.force_sub_service import check_force_sub
import time

router = Router()
bypass_manager = BypassManager()
_cooldowns = {}

def is_premium(user):
    if user.get("is_premium"):
        return True
    return False

@router.message(F.text & ~F.text.startswith("/"))
async def handle_message(message: Message, bot: Bot):
    url = extract_url(message.text)
    if not url:
        return

    user_id = message.from_user.id
    user = await get_or_create_user(user_id, message.from_user)

    if user.get("is_banned"):
        return

    fsub = await check_force_sub(user_id, bot)
    if not fsub["passed"]:
        buttons = []
        for ch in fsub["missing"]:
            clean = ch.replace("@", "")
            buttons.append([InlineKeyboardButton(text=f"\U0001f4e2 Join {ch}", url=f"https://t.me/{clean}")])
        buttons.append([InlineKeyboardButton(text="\u2705 I've Joined \u2014 Verify", callback_data=f"verify_fsub:{url}")])
        await message.reply("\U0001f4e2 Please join the following channels to use this bot:", 
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        return

    prem = is_premium(user)

    if not prem:
        daily_limit = int(await get_setting("free_daily_limit") or "5")
        if user.get("daily_bypasses_used", 0) >= daily_limit:
            stars_price = await get_setting("premium_stars_price") or "50"
            ref_count = await get_setting("premium_referral_count") or "3"
            await message.reply(
                f"\u26a0\ufe0f Daily limit reached! ({user['daily_bypasses_used']}/{daily_limit})\n\n"
                f"\u2b50 Get Premium ({stars_price} Stars) for unlimited bypasses!\n"
                f"\U0001f465 Or invite {ref_count} friends for FREE premium!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=f"\u2b50 Get Premium", callback_data="buy_premium_stars")],
                    [InlineKeyboardButton(text="\U0001f465 Invite Friends", callback_data="referral_menu")]
                ]))
            return

        cooldown = int(await get_setting("cooldown_seconds") or "10")
        now = time.time()
        if user_id in _cooldowns and now - _cooldowns[user_id] < cooldown:
            remaining = int(cooldown - (now - _cooldowns[user_id]))
            await message.reply(f"\u23f3 Please wait {remaining} seconds between bypasses.")
            return
        _cooldowns[user_id] = now

    clean_url = bypass_manager.clean_url(url)

    if not bypass_manager.is_shortener_url(clean_url):
        pass

    shortener_name = bypass_manager.identify_shortener(clean_url)
    if shortener_name == "Unknown":
        shortener_name = "Unknown shortener"

    processing_msg = await message.reply(f"\U0001f513 Bypassing {shortener_name}...\n\u23f3 Please wait...")

    result = await bypass_manager.bypass(clean_url)

    if not result.success:
        await processing_msg.edit_text(
            f"\u274c Could not bypass this link.\n\n"
            f"\U0001f3f7\ufe0f Shortener: {shortener_name}\n"
            f"\u2139\ufe0f {result.error}\n\n"
            f"\U0001f4a1 Tip: Try again later or open in browser with an adblocker.")
        return

    injection = await link_injector.inject(result.destination, prem)

    await save_bypass_history(user_id, clean_url, shortener_name, result.destination,
        injection["final_url"] if not injection["is_direct"] else None, result.method, result.time_ms)
    await increment_daily_bypass(user_id)

    link_to_show = injection["final_url"]

    if prem:
        await processing_msg.edit_text(
            f"\u26a1 Link Bypassed Instantly!\n\n"
            f"\U0001f517 Original: {truncate(clean_url, 40)}\n"
            f"\U0001f3f7\ufe0f Shortener: {shortener_name}\n"
            f"\u26a1 Speed: {result.time_ms}ms\n\n"
            f"\U0001f4ce Direct destination:\n{result.destination}\n\n"
            f"\u2b50 Premium \u2014 No ads, instant access!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="\U0001f517 Open Link", url=result.destination)],
                [InlineKeyboardButton(text="\U0001f4e4 Share Bot", callback_data="share_bot")]
            ]),
            disable_web_page_preview=True)
    else:
        used = user.get("daily_bypasses_used", 0) + 1
        daily_limit = int(await get_setting("free_daily_limit") or "5")
        note = "\n\U0001f4a1 Opens in browser \u2192 wait a few seconds \u2192 destination loads!" if not injection["is_direct"] else ""

        await processing_msg.edit_text(
            f"\u2705 Link Bypassed Successfully!\n\n"
            f"\U0001f517 Original: {truncate(clean_url, 40)}\n"
            f"\U0001f3f7\ufe0f Shortener: {shortener_name}\n"
            f"\u26a1 Speed: {result.time_ms}ms\n\n"
            f"\U0001f4ce Your link:\n{link_to_show}\n{note}\n\n"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
            f"\U0001f4ca Today: {used}/{daily_limit}\n"
            f"\u2b50 Get Premium for instant direct links!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="\U0001f517 Open Link", url=link_to_show)],
                [InlineKeyboardButton(text="\u2b50 Premium", callback_data="premium_menu"),
                 InlineKeyboardButton(text="\U0001f465 Free via Referral", callback_data="referral_menu")],
            ]),
            disable_web_page_preview=True)

@router.callback_query(F.data.startswith("verify_fsub:"))
async def verify_fsub(callback: CallbackQuery, bot: Bot):
    url = callback.data.split(":", 1)[1]
    fsub = await check_force_sub(callback.from_user.id, bot)
    if fsub["passed"]:
        await callback.message.edit_text("\u2705 Verified! Send the link again to bypass it.")
    else:
        await callback.answer("\u274c You haven't joined all channels yet.", show_alert=True)

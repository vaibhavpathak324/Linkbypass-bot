"""
LinkBypass Pro — Premium Handler
==================================
"""
import logging, datetime
from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery
from aiogram.filters import Command
from bot.database.db import get_or_create_user, get_setting, is_user_premium, grant_premium

logger = logging.getLogger(__name__)
router = Router()

@router.callback_query(F.data == "show_premium")
async def show_premium(callback: CallbackQuery):
    is_prem = await is_user_premium(callback.from_user.id)
    stars_price = int(await get_setting('premium_stars_price', '150'))
    stars_days = int(await get_setting('premium_stars_days', '30'))
    ref_count = int(await get_setting('premium_referral_count', '3'))
    ref_days = int(await get_setting('premium_referral_days', '3'))
    text = (
        f"⭐ Premium Membership\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{'✅ You are Premium!' if is_prem else '👤 Free Plan'}\n\n"
        f"Premium Benefits:\n"
        f"├── ♾ Unlimited daily bypasses\n"
        f"├── 📦 Batch bypass (25 links)\n"
        f"├── ⚡ Priority processing\n"
        f"├── 🚫 No ads or injection\n"
        f"└── 🎯 Direct links always\n\n"
        f"How to get Premium:\n"
        f"1️⃣ ⭐ Telegram Stars: {stars_price} Stars = {stars_days} days\n"
        f"2️⃣ 👥 Referrals: Invite {ref_count} friends = {ref_days} days free\n"
    )
    buttons = []
    stars_enabled = await get_setting('premium_stars_enabled', 'true')
    if stars_enabled == 'true' and not is_prem:
        buttons.append([InlineKeyboardButton(text=f"⭐ Buy with {stars_price} Stars", callback_data="buy_premium_stars")])
    buttons.append([InlineKeyboardButton(text="👥 Referral Program", callback_data="show_referral")])
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="back_start")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@router.callback_query(F.data == "buy_premium_stars")
async def buy_premium(callback: CallbackQuery, bot: Bot):
    stars_price = int(await get_setting('premium_stars_price', '150'))
    stars_days = int(await get_setting('premium_stars_days', '30'))
    prices = [LabeledPrice(label=f"Premium {stars_days} Days", amount=stars_price)]
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"⭐ Premium {stars_days} Days",
        description=f"Unlimited bypasses, batch mode, no ads for {stars_days} days",
        payload=f"premium_{stars_days}",
        provider_token="",  # Empty for Telegram Stars
        currency="XTR",
        prices=prices,
    )
    await callback.answer()

@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)

@router.message(F.successful_payment)
async def successful_payment(message: Message):
    payment = message.successful_payment
    if payment.invoice_payload.startswith("premium_"):
        days = int(payment.invoice_payload.split("_")[1])
        await grant_premium(message.from_user.id, days, "stars")
        await message.answer(f"🎉 Premium activated for {days} days!\n\nEnjoy unlimited bypasses! ⭐")

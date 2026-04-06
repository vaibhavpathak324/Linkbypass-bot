from aiogram import Router, Bot, F
from aiogram.types import (Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    LabeledPrice, PreCheckoutQuery)
from aiogram.filters import Command
from bot.database.db import get_or_create_user, get_setting, get_db
from bot.config import ADMIN_USER_ID

router = Router()

@router.message(Command("premium"))
async def cmd_premium(message: Message):
    await show_premium(message, message.from_user.id)

@router.callback_query(F.data == "premium_menu")
async def cb_premium(callback: CallbackQuery):
    await show_premium(callback.message, callback.from_user.id, edit=True)
    await callback.answer()

async def show_premium(msg, user_id, edit=False):
    user = await get_or_create_user(user_id)
    stars_price = await get_setting("premium_stars_price") or "50"
    stars_days = await get_setting("premium_stars_days") or "30"
    ref_count = await get_setting("premium_referral_count") or "3"
    ref_days = await get_setting("premium_referral_days") or "3"
    
    status = "⭐ PREMIUM" if user.get("is_premium") else "🆓 Free"
    
    text = (
        f"⭐ Premium Membership\n\n"
        f"Your status: {status}\n\n"
        f"Benefits:\n"
        f"✅ Unlimited bypasses (no daily limit)\n"
        f"✅ Direct links (no ad pages)\n"
        f"✅ No cooldown between bypasses\n"
        f"✅ Batch bypass up to 50 links\n"
        f"✅ Priority support\n\n"
        f"💫 Option 1: {stars_price} Telegram Stars ({stars_days} days)\n"
        f"👥 Option 2: Invite {ref_count} friends ({ref_days} days FREE)"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"⭐ Buy with {stars_price} Stars", callback_data="buy_premium_stars")],
        [InlineKeyboardButton(text="👥 Invite Friends (FREE)", callback_data="referral_menu")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="back_start")]
    ])
    
    if edit:
        await msg.edit_text(text, reply_markup=kb)
    else:
        await msg.answer(text, reply_markup=kb)

@router.callback_query(F.data == "buy_premium_stars")
async def buy_stars(callback: CallbackQuery, bot: Bot):
    stars_enabled = await get_setting("premium_stars_enabled")
    if stars_enabled != "true":
        await callback.answer("Stars payment is currently disabled.", show_alert=True)
        return
    
    price = int(await get_setting("premium_stars_price") or "50")
    days = await get_setting("premium_stars_days") or "30"
    
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="⭐ LinkBypass Pro Premium",
        description=f"Unlimited bypasses, direct links, no cooldown for {days} days!",
        payload=f"premium_{callback.from_user.id}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=f"Premium {days} Days", amount=price)]
    )
    await callback.answer()

@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)

@router.message(F.successful_payment)
async def successful_payment(message: Message, bot: Bot):
    user_id = message.from_user.id
    days = int(await get_setting("premium_stars_days") or "30")
    db = await get_db()
    await db.execute(
        "UPDATE users SET is_premium=1, premium_source='stars', premium_until=datetime('now', '+' || ? || ' days') WHERE user_id=?",
        (days, user_id))
    await db.commit()
    
    await message.answer(f"🎉 Premium activated for {days} days! Enjoy unlimited bypasses! ⭐")
    try:
        await bot.send_message(ADMIN_USER_ID, f"💰 New premium purchase!\nUser: {message.from_user.full_name} ({user_id})\nStars: {message.successful_payment.total_amount}")
    except:
        pass

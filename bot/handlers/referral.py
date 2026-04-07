"""
LinkBypass Pro — Referral Handler
"""
import logging
from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from bot.database.db import get_or_create_user, get_setting

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("referral"))
async def cmd_referral(message: Message):
    await _show_referral(message)

@router.callback_query(F.data == "show_referral")
async def cb_referral(callback: CallbackQuery):
    user = await get_or_create_user(callback.from_user.id, callback.from_user)
    me = await callback.bot.get_me()
    ref_link = f"https://t.me/{me.username}?start=ref_{user['referral_code']}"
    ref_count = int(await get_setting('premium_referral_count', '3'))
    ref_days = int(await get_setting('premium_referral_days', '3'))
    bonus = int(await get_setting('referral_bonus_credits', '5'))
    text = (
        f"👥 Referral Program\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 Your Stats:\n"
        f"├── Referrals: {user['total_referrals']}\n"
        f"├── Bonus Credits: {user['bonus_credits']}\n"
        f"└── Code: {user['referral_code']}\n\n"
        f"🎁 Rewards:\n"
        f"• Each referral = +{bonus} bonus bypasses\n"
        f"• {ref_count} referrals = {ref_days} days Premium!\n\n"
        f"📎 Your Referral Link:\n{ref_link}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Share Link", switch_inline_query=f"Join me on LinkBypass Pro! {ref_link}")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="back_start")],
    ])
    await callback.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
    await callback.answer()

async def _show_referral(message: Message):
    user = await get_or_create_user(message.from_user.id, message.from_user)
    me = await message.bot.get_me()
    ref_link = f"https://t.me/{me.username}?start=ref_{user['referral_code']}"
    await message.answer(
        f"👥 Your Referral Link:\n{ref_link}\n\n"
        f"Referrals: {user['total_referrals']} | Credits: {user['bonus_credits']}",
        disable_web_page_preview=True
    )

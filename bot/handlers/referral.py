from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from bot.database.db import get_or_create_user, get_setting

router = Router()

@router.message(Command("referral"))
async def cmd_referral(message: Message, bot: Bot):
    user = await get_or_create_user(message.from_user.id, message.from_user)
    me = await bot.get_me()
    ref_code = user.get("referral_code", "")
    ref_count = int(await get_setting("premium_referral_count") or "3")
    ref_days = int(await get_setting("premium_referral_days") or "3")
    total = user.get("total_referrals", 0)
    progress = min(total, ref_count)
    bar = "█" * progress + "░" * (ref_count - progress)
    link = f"https://t.me/{me.username}?start=ref_{ref_code}"
    text = f"👥 Get FREE Premium!\n\n🔗 Your link:\n{link}\n\n📊 {bar} {total}/{ref_count}\n\n🎁 Reward: {ref_days} days unlimited!"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Share", switch_inline_query=f"Join LinkBypass Pro! {link}")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="back_start")]
    ])
    await message.answer(text, reply_markup=kb, disable_web_page_preview=True)

@router.callback_query(F.data == "referral_menu")
async def cb_referral(callback: CallbackQuery, bot: Bot):
    user = await get_or_create_user(callback.from_user.id, callback.from_user)
    me = await bot.get_me()
    ref_code = user.get("referral_code", "")
    ref_count = int(await get_setting("premium_referral_count") or "3")
    total = user.get("total_referrals", 0)
    link = f"https://t.me/{me.username}?start=ref_{ref_code}"
    await callback.message.edit_text(f"👥 Referral\n\n🔗 {link}\n\n📊 {total}/{ref_count}", disable_web_page_preview=True)
    await callback.answer()

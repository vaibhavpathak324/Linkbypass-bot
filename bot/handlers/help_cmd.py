"""
LinkBypass Pro — Help Handler
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from bot.engine.domain_list import get_total_count, get_category_counts

router = Router()

@router.message(Command("help"))
async def cmd_help(message: Message):
    await _send_help(message)

@router.callback_query(F.data == "show_help")
async def cb_help(callback: CallbackQuery):
    total = get_total_count()
    cats = get_category_counts()
    text = (
        f"ℹ️ Help — LinkBypass Pro\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🤖 Commands:\n"
        f"├── /start — Main menu\n"
        f"├── /help — This help page\n"
        f"├── /history — Bypass history\n"
        f"├── /premium — Premium info\n"
        f"├── /referral — Referral program\n"
        f"├── /check <url> — Check if URL is supported\n"
        f"└── /language — Change language\n\n"
        f"🔓 Bypass Engine:\n"
        f"├── {total}+ shorteners supported\n"
        f"├── 5-layer bypass system\n"
        f"├── AdLinkFly sites: {cats.get('adlinkfly', 0)}\n"
        f"├── Redirect sites: {cats.get('redirect', 0)}\n"
        f"├── JS-based sites: {cats.get('js_based', 0)}\n"
        f"└── Multi-step sites: {cats.get('multi_step', 0)}\n\n"
        f"📌 Just send any short link to bypass it!"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="back_start")]
    ])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

async def _send_help(message: Message):
    total = get_total_count()
    await message.answer(
        f"ℹ️ LinkBypass Pro — {total}+ shorteners supported\n\n"
        f"Just send me any shortened URL and I'll bypass it!\n\n"
        f"Commands: /start /help /history /premium /referral /check /language"
    )

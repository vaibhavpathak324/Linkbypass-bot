"""
LinkBypass Pro — Language Handler
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from bot.database.db import update_user

router = Router()

LANGUAGES = {
    'en': '🇬🇧 English',
    'hi': '🇮🇳 Hindi',
}

@router.message(Command("language"))
async def cmd_language(message: Message):
    buttons = [[InlineKeyboardButton(text=name, callback_data=f"setlang_{code}")] for code, name in LANGUAGES.items()]
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="back_start")])
    await message.answer("🌐 Select Language:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data == "show_language")
async def cb_language(callback: CallbackQuery):
    buttons = [[InlineKeyboardButton(text=name, callback_data=f"setlang_{code}")] for code, name in LANGUAGES.items()]
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="back_start")])
    await callback.message.edit_text("🌐 Select Language:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@router.callback_query(F.data.startswith("setlang_"))
async def set_language(callback: CallbackQuery):
    lang = callback.data.split("_")[1]
    await update_user(callback.from_user.id, language=lang)
    await callback.answer(f"✅ Language set to {LANGUAGES.get(lang, lang)}", show_alert=True)

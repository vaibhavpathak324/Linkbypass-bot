from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from bot.database.db import get_db

router = Router()

@router.message(Command("language"))
async def cmd_lang(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\U0001f1ec\U0001f1e7 English", callback_data="set_lang:en"),
         InlineKeyboardButton(text="\U0001f1ee\U0001f1f3 Hindi", callback_data="set_lang:hi")]
    ])
    await message.answer("\U0001f310 Choose Language:", reply_markup=kb)

@router.callback_query(F.data.startswith("set_lang:"))
async def set_lang(callback: CallbackQuery):
    lang = callback.data.split(":")[1]
    db = await get_db()
    await db.execute("UPDATE users SET language=? WHERE user_id=?", (lang, callback.from_user.id))
    await db.commit()
    name = "English" if lang == "en" else "Hindi"
    await callback.message.edit_text(f"\u2705 Language set to {name}")
    await callback.answer()

@router.callback_query(F.data == "language_menu")
async def cb_lang(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\U0001f1ec\U0001f1e7 English", callback_data="set_lang:en"),
         InlineKeyboardButton(text="\U0001f1ee\U0001f1f3 Hindi", callback_data="set_lang:hi")]
    ])
    await callback.message.edit_text("\U0001f310 Choose Language:", reply_markup=kb)
    await callback.answer()

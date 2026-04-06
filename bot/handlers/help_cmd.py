from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

router = Router()

HELP_TEXT = "\u2753 How to Use LinkBypass Pro\n\n1\ufe0f\u20e3 Send any shortened link\n2\ufe0f\u20e3 Bot bypasses it instantly\n3\ufe0f\u20e3 Tap Open Link to access\n\n\U0001f4e6 Batch: /batch\n\U0001f4cb History: /history\n\U0001f310 Language: /language\n\u2b50 Premium: /premium\n\U0001f465 Invite: /referral"

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(HELP_TEXT)

@router.callback_query(F.data == "help")
async def cb_help(callback: CallbackQuery):
    await callback.message.edit_text(HELP_TEXT)
    await callback.answer()

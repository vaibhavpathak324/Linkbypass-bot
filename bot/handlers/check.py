from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from bot.engine.domain_list import KNOWN_SHORTENER_DOMAINS

router = Router()

@router.message(Command("supported"))
async def cmd_supported(message: Message):
    count = len(KNOWN_SHORTENER_DOMAINS)
    text = f"\U0001f310 Supported Shorteners ({count}+)\n\n\U0001f4cc Major: Linkvertise, ShrinkMe, GPLinks, OUO, AdFly, Exe.io\n\n\U0001f4cc Indian: VPLink, AroLinks, LinkShortify, EarnLink\n\n\U0001f4cc Total: {count}+ shorteners supported!\n\nSend any link to try! \U0001f513"
    await message.answer(text)

@router.callback_query(F.data == "supported")
async def cb_supported(callback: CallbackQuery):
    count = len(KNOWN_SHORTENER_DOMAINS)
    await callback.message.edit_text(f"\U0001f310 Supported: {count}+ shorteners")
    await callback.answer()

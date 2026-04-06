from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from bot.database.db import get_or_create_user, get_setting
from bot.engine.manager import BypassManager
from bot.engine.url_utils import extract_url, truncate
from bot.injection.injector import link_injector
import re

router = Router()
bypass_manager = BypassManager()

@router.message(Command("batch"))
async def cmd_batch(message: Message):
    user = await get_or_create_user(message.from_user.id, message.from_user)
    prem = user.get("is_premium", 0)
    limit = int(await get_setting("batch_limit_premium" if prem else "batch_limit_free") or "3")
    await message.answer(f"\U0001f4e6 Batch Bypass\n\nSend up to {limit} links, one per line.")

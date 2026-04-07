"""
LinkBypass Pro — Force Subscribe Service
"""
import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.database.db import get_setting, get_force_sub_channels

logger = logging.getLogger(__name__)

async def check_force_sub(bot: Bot, user_id: int) -> bool:
    enabled = await get_setting("force_sub_enabled", "false")
    if enabled != "true":
        return True
    channels = await get_force_sub_channels()
    if not channels:
        return True
    not_joined = []
    for ch in channels:
        try:
            member = await bot.get_chat_member(ch['channel_id'] or ch['channel_username'], user_id)
            if member.status in ('left', 'kicked', 'banned'):
                not_joined.append(ch)
        except Exception:
            pass  # Skip channels we can't check
    if not not_joined:
        return True
    buttons = []
    for ch in not_joined:
        buttons.append([InlineKeyboardButton(text=f"📢 Join {ch['channel_username']}", url=f"https://t.me/{ch['channel_username'].lstrip('@')}")])
    buttons.append([InlineKeyboardButton(text="✅ I Joined", callback_data="check_fsub")])
    from aiogram.types import Message
    # We need to send this via the bot directly
    try:
        await bot.send_message(
            user_id,
            "📢 Please join our channels to use the bot:\n\n" +
            "\n".join(f"• {ch['channel_username']}" for ch in not_joined),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    except Exception:
        pass
    return False

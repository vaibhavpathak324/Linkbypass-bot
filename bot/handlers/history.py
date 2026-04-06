from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from bot.database.db import get_db
from bot.engine.url_utils import truncate

router = Router()

@router.message(Command("history"))
async def cmd_history(message: Message):
    db = await get_db()
    cur = await db.execute("SELECT * FROM bypass_history WHERE user_id=? ORDER BY created_at DESC LIMIT 15", (message.from_user.id,))
    rows = await cur.fetchall()
    if not rows:
        await message.answer("\U0001f4cb No bypass history yet.")
        return
    text = "\U0001f4cb Your Bypass History (last 15):\n\n"
    for i, r in enumerate(rows, 1):
        text += f"{i}. \U0001f513 {truncate(r['original_url'],30)} -> {truncate(r['destination_url'],30)}\n   {r['time_taken']}ms | {r['shortener']}\n\n"
    await message.answer(text)

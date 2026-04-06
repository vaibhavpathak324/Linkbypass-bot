from aiogram import Router, Bot, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import CommandStart
from bot.database.db import get_or_create_user, get_setting, get_db, get_user_count
from bot.engine.domain_list import KNOWN_SHORTENER_DOMAINS
from bot.services.force_sub_service import check_force_sub

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    user = await get_or_create_user(message.from_user.id, message.from_user)
    
    # Handle referral deep link
    args = message.text.split(maxsplit=1)
    if len(args) > 1 and args[1].startswith("ref_"):
        ref_code = args[1][4:]
        db = await get_db()
        cur = await db.execute("SELECT * FROM users WHERE referral_code=?", (ref_code,))
        referrer = await cur.fetchone()
        if referrer and referrer["user_id"] != message.from_user.id and not user.get("referred_by"):
            await db.execute("UPDATE users SET referred_by=? WHERE user_id=?", (referrer["user_id"], message.from_user.id))
            await db.execute("UPDATE users SET total_referrals=total_referrals+1 WHERE user_id=?", (referrer["user_id"],))
            bonus = int(await get_setting("referral_bonus_credits") or "5")
            await db.execute("UPDATE users SET bonus_credits=bonus_credits+? WHERE user_id=?", (bonus, referrer["user_id"]))
            await db.execute("UPDATE users SET bonus_credits=bonus_credits+? WHERE user_id=?", (bonus, message.from_user.id))
            await db.commit()
            
            # Check if referrer earned premium
            ref_count = int(await get_setting("premium_referral_count") or "3")
            ref_days = int(await get_setting("premium_referral_days") or "3")
            cur2 = await db.execute("SELECT total_referrals FROM users WHERE user_id=?", (referrer["user_id"],))
            rr = await cur2.fetchone()
            if rr and rr["total_referrals"] >= ref_count:
                ref_enabled = await get_setting("premium_referral_enabled")
                if ref_enabled == "true":
                    await db.execute(
                        "UPDATE users SET is_premium=1, premium_source='referral', premium_until=datetime('now', '+' || ? || ' days') WHERE user_id=?",
                        (ref_days, referrer["user_id"]))
                    await db.commit()
                    try:
                        await bot.send_message(referrer["user_id"],
                            f"🎉 You invited {ref_count} friends! {ref_days} days FREE premium activated! 🚀")
                    except:
                        pass
            try:
                await bot.send_message(referrer["user_id"],
                    f"🎉 {message.from_user.full_name} joined via your link!")
            except:
                pass
    
    limit = await get_setting("free_daily_limit") or "5"
    count = len(KNOWN_SHORTENER_DOMAINS)
    
    welcome = await get_setting("welcome_message") or "🔓 Welcome to LinkBypass Pro!"
    
    text = (
        f"{welcome}\n\n"
        f"📊 I support {count}+ shorteners!\n\n"
        f"🔓 Bypasses today: {user.get('daily_bypasses_used', 0)}/{limit}"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔓 Supported Shorteners", callback_data="supported"),
         InlineKeyboardButton(text="⭐ Premium", callback_data="premium_menu")],
        [InlineKeyboardButton(text="👥 Invite & Earn", callback_data="referral_menu"),
         InlineKeyboardButton(text="🌐 Language", callback_data="language_menu")],
        [InlineKeyboardButton(text="❓ Help", callback_data="help")]
    ])
    await message.answer(text, reply_markup=kb)

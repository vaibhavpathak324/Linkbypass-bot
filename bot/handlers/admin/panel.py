from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.config import ADMIN_USER_ID
from bot.database.db import (get_db, get_setting, set_setting, get_user_count,
    get_active_shortener_configs, get_all_user_ids)
from bot.engine.domain_list import KNOWN_SHORTENER_DOMAINS
import httpx, time, datetime

router = Router()
_start_time = time.time()

class AdminStates(StatesGroup):
    waiting_shortener_key = State()
    waiting_setting_value = State()
    waiting_broadcast = State()
    waiting_user_search = State()
    waiting_channel = State()
    waiting_custom_name = State()
    waiting_custom_endpoint = State()
    waiting_custom_key = State()
    waiting_custom_format = State()

def is_admin(user_id):
    return user_id == ADMIN_USER_ID

ADMIN_KB = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📊 Dashboard", callback_data="admin_dashboard"),
     InlineKeyboardButton(text="👥 Users", callback_data="admin_users")],
    [InlineKeyboardButton(text="🔗 My Shorteners", callback_data="admin_shorteners"),
     InlineKeyboardButton(text="📢 Force Subscribe", callback_data="admin_forcesub")],
    [InlineKeyboardButton(text="💰 Revenue", callback_data="admin_revenue"),
     InlineKeyboardButton(text="🔓 Bypass Stats", callback_data="admin_bypass_stats")],
    [InlineKeyboardButton(text="📣 Broadcast", callback_data="admin_broadcast"),
     InlineKeyboardButton(text="⚙️ Settings", callback_data="admin_settings")],
])

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Admin access only.")
        return
    await message.answer("🔧 LinkBypass Pro — Admin Panel\n━━━━━━━━━━━━━━━━━━━━━━━━━━━", reply_markup=ADMIN_KB)

@router.callback_query(F.data == "admin_menu")
async def cb_admin_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    await callback.message.edit_text("🔧 LinkBypass Pro — Admin Panel\n━━━━━━━━━━━━━━━━━━━━━━━━━━━", reply_markup=ADMIN_KB)
    await callback.answer()

@router.callback_query(F.data == "admin_dashboard")
async def dashboard(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    db = await get_db()
    total = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
    today = datetime.date.today().isoformat()
    new_today = (await (await db.execute("SELECT COUNT(*) FROM users WHERE date(joined_at)=?", (today,))).fetchone())[0]
    premium = (await (await db.execute("SELECT COUNT(*) FROM users WHERE is_premium=1")).fetchone())[0]
    banned = (await (await db.execute("SELECT COUNT(*) FROM users WHERE is_banned=1")).fetchone())[0]
    bypasses_today = (await (await db.execute("SELECT COUNT(*) FROM bypass_history WHERE date(created_at)=?", (today,))).fetchone())[0]
    total_bypasses = (await (await db.execute("SELECT COUNT(*) FROM bypass_history")).fetchone())[0]
    configs = await get_active_shortener_configs()
    uptime = int(time.time() - _start_time)
    h, m = uptime // 3600, (uptime % 3600) // 60
    text = (f"📊 Dashboard — {today}\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Users: {total} (New: {new_today}, Premium: {premium}, Banned: {banned})\n\n"
        f"🔓 Bypasses: Today {bypasses_today} | Total {total_bypasses}\n\n"
        f"🔗 Shortener APIs: {len(configs)} active\n🤖 Uptime: {h}h {m}m")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Refresh", callback_data="admin_dashboard"),
         InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu")]])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

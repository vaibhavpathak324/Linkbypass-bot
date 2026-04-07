"""
LinkBypass Pro — Admin Panel
==============================
Complete admin panel with dashboard, user management,
shortener config, bypass stats, revenue tracking,
broadcast, force-subscribe, and settings.
"""

import time
import datetime
import logging
import httpx
from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.config import ADMIN_USER_ID
from bot.database.db import (
    get_db, get_setting, set_setting, get_user_count,
    get_active_shortener_configs, get_all_shortener_configs,
    get_all_user_ids, get_top_users, get_recent_users,
    search_user, ban_user, unban_user, grant_premium,
    upsert_shortener_config, delete_shortener_config,
    toggle_shortener_config, get_bypass_stats,
    get_api_stats, get_analytics_range, update_daily_analytics,
    add_force_sub_channel, get_force_sub_channels,
)
from bot.engine.domain_list import get_total_count

logger = logging.getLogger(__name__)
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
    waiting_ban_reason = State()


SHORTENER_PRESETS = {
    "shrinkme": {"name": "Shrinkme.io", "endpoint": "https://shrinkme.io/api?api={key}&url={url}", "format": "json_shortenedUrl"},
    "gplinks": {"name": "GPLinks.com", "endpoint": "https://gplinks.com/api?api={key}&url={url}", "format": "json_shortenedUrl"},
    "linkshortify": {"name": "Linkshortify", "endpoint": "https://linkshortify.com/api?api={key}&url={url}", "format": "json_shortenedUrl"},
    "arolinks": {"name": "AroLinks", "endpoint": "https://arolinks.com/api?api={key}&url={url}", "format": "json_shortenedUrl"},
    "ouo": {"name": "OUO.io", "endpoint": "https://ouo.io/api/{key}?s={url}", "format": "plain_text"},
    "exeio": {"name": "Exe.io", "endpoint": "https://exe.io/api?api={key}&url={url}", "format": "json_shortenedUrl"},
    "fclc": {"name": "FC.lc", "endpoint": "https://fc.lc/api?api={key}&url={url}", "format": "json_shortenedUrl"},
    "shortest": {"name": "Shorte.st", "endpoint": "https://api.shorte.st/v1/data/url", "format": "json_shortenedUrl"},
    "clicksfly": {"name": "ClicksFly", "endpoint": "https://clicksfly.com/api?api={key}&url={url}", "format": "json_shortenedUrl"},
    "droplink": {"name": "DropLink", "endpoint": "https://droplink.co/api?api={key}&url={url}", "format": "json_shortenedUrl"},
}


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
    [InlineKeyboardButton(text="📈 API Health", callback_data="admin_api_health")],
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
    new_today = (await (await db.execute("SELECT COUNT(*) FROM users WHERE date(created_at)=?", (today,))).fetchone())[0]
    premium = (await (await db.execute("SELECT COUNT(*) FROM users WHERE is_premium=1")).fetchone())[0]
    banned = (await (await db.execute("SELECT COUNT(*) FROM users WHERE is_banned=1")).fetchone())[0]
    bypasses_today = (await (await db.execute("SELECT COUNT(*) FROM bypass_history WHERE date(created_at)=?", (today,))).fetchone())[0]
    total_bypasses = (await (await db.execute("SELECT COUNT(*) FROM bypass_history")).fetchone())[0]
    successful = (await (await db.execute("SELECT COUNT(*) FROM bypass_history WHERE success=1")).fetchone())[0]
    configs = await get_active_shortener_configs()
    uptime = int(time.time() - _start_time)
    h, m = uptime // 3600, (uptime % 3600) // 60
    success_rate = round(successful / max(total_bypasses, 1) * 100, 1)
    text = (
        f"📊 Dashboard — {today}\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Users:\n├── Total: {total}\n├── New today: {new_today}\n├── Premium: {premium}\n└── Banned: {banned}\n\n"
        f"🔓 Bypasses:\n├── Today: {bypasses_today}\n├── Total: {total_bypasses}\n└── Success Rate: {success_rate}%\n\n"
        f"🔗 Shortener APIs: {len(configs)} active\n"
        f"🌐 Supported Domains: {get_total_count()}+\n"
        f"🤖 Uptime: {h}h {m}m"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Refresh", callback_data="admin_dashboard"),
         InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu")]])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


# ── User Management ────────────────────────────────────────

@router.callback_query(F.data == "admin_users")
async def users_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    total = await get_user_count()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Find User", callback_data="admin_find_user")],
        [InlineKeyboardButton(text="📋 Top 10", callback_data="admin_top_users"),
         InlineKeyboardButton(text="🆕 Recent 20", callback_data="admin_recent_users")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu")]])
    await callback.message.edit_text(f"👥 User Management ({total} total)", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "admin_find_user")
async def find_user(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await callback.message.edit_text("Send user ID to search:")
    await state.set_state(AdminStates.waiting_user_search)
    await callback.answer()

@router.message(AdminStates.waiting_user_search)
async def process_user_search(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.clear()
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Invalid user ID.")
        return
    user = await search_user(uid)
    if not user:
        await message.answer("❌ User not found.")
        return
    text = (
        f"👤 User Info\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 ID: {user['user_id']}\n"
        f"👤 Name: {user['full_name']}\n"
        f"📧 Username: @{user['username'] or 'N/A'}\n"
        f"⭐ Premium: {'Yes' if user['is_premium'] else 'No'}\n"
        f"🚫 Banned: {'Yes' if user['is_banned'] else 'No'}\n"
        f"📊 Bypasses: {user['total_bypasses']} (today: {user['daily_bypasses_used']})\n"
        f"👥 Referrals: {user['total_referrals']}\n"
        f"📅 Joined: {user['created_at']}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 Ban" if not user['is_banned'] else "✅ Unban", callback_data=f"admin_toggleban_{uid}"),
         InlineKeyboardButton(text="⭐ Give Premium", callback_data=f"admin_giveprem_{uid}")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_users")]])
    await message.answer(text, reply_markup=kb)

@router.callback_query(F.data.startswith("admin_toggleban_"))
async def toggle_ban(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    uid = int(callback.data.split("_")[2])
    user = await search_user(uid)
    if user and user['is_banned']:
        await unban_user(uid)
        await callback.answer("✅ User unbanned", show_alert=True)
    else:
        await ban_user(uid, "Admin action")
        await callback.answer("🚫 User banned", show_alert=True)

@router.callback_query(F.data.startswith("admin_giveprem_"))
async def give_premium(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    uid = int(callback.data.split("_")[2])
    await grant_premium(uid, 30, "admin_gift")
    await callback.answer("⭐ 30 days Premium granted!", show_alert=True)

@router.callback_query(F.data == "admin_top_users")
async def top_users(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    users = await get_top_users(10)
    text = "📋 Top 10 Users (by bypasses):\n\n"
    for i, u in enumerate(users, 1):
        text += f"{i}. {u['full_name'][:20]} — {u['total_bypasses']} bypasses {'⭐' if u['is_premium'] else ''}\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="admin_users")]])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "admin_recent_users")
async def recent_users(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    users = await get_recent_users(20)
    text = "🆕 Recent 20 Users:\n\n"
    for i, u in enumerate(users, 1):
        text += f"{i}. {u['full_name'][:15]} (ID: {u['user_id']}) — {str(u['created_at'])[:10]}\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="admin_users")]])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


# ── Shortener Management ──────────────────────────────────

@router.callback_query(F.data == "admin_shorteners")
async def shorteners_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    configs = await get_all_shortener_configs()
    text = f"🔗 Shortener Configs ({len(configs)} total)\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for c in configs:
        status = "✅" if c['is_active'] else "❌"
        text += f"{status} {c['display_name']} — {c['total_links_created']} links\n"
    if not configs:
        text += "No shorteners configured yet.\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add Preset", callback_data="admin_add_preset"),
         InlineKeyboardButton(text="➕ Custom", callback_data="admin_custom_short")],
        [InlineKeyboardButton(text="🔄 Rotation", callback_data="admin_rotation"),
         InlineKeyboardButton(text="🧪 Test APIs", callback_data="admin_test_apis")],
        [InlineKeyboardButton(text="💉 Toggle Injection", callback_data="admin_toggle_inject")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu")]])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "admin_add_preset")
async def add_preset(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    buttons = []
    for key, preset in SHORTENER_PRESETS.items():
        buttons.append([InlineKeyboardButton(text=preset['name'], callback_data=f"admin_preset_{key}")])
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="admin_shorteners")])
    await callback.message.edit_text("Choose a preset shortener:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@router.callback_query(F.data.startswith("admin_preset_"))
async def select_preset(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    key = callback.data.replace("admin_preset_", "")
    preset = SHORTENER_PRESETS.get(key)
    if not preset:
        await callback.answer("Invalid preset", show_alert=True)
        return
    await state.update_data(preset_key=key, preset_data=preset)
    await callback.message.edit_text(f"Send your API key for {preset['name']}:")
    await state.set_state(AdminStates.waiting_shortener_key)
    await callback.answer()

@router.message(AdminStates.waiting_shortener_key)
async def process_shortener_key(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    data = await state.get_data()
    await state.clear()
    api_key = message.text.strip()
    preset = data.get('preset_data', {})
    key = data.get('preset_key', '')
    name = preset.get('name', key)
    endpoint = preset.get('endpoint', '')
    fmt = preset.get('format', 'json_shortenedUrl')

    # Test the API
    test_ep = endpoint.replace("{key}", api_key).replace("{url}", "https://google.com")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(test_ep)
            if resp.status_code == 200:
                await upsert_shortener_config(key, name, api_key, endpoint, fmt)
                await message.answer(f"✅ {name} configured successfully!")
                return
        await message.answer(f"❌ API test failed (status {resp.status_code}).")
    except Exception as e:
        await message.answer(f"❌ API test error: {str(e)[:100]}")

@router.callback_query(F.data == "admin_custom_short")
async def custom_short(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await callback.message.edit_text("Send shortener name (e.g. MyShortener):")
    await state.set_state(AdminStates.waiting_custom_name)
    await callback.answer()

@router.message(AdminStates.waiting_custom_name)
async def custom_name(message: Message, state: FSMContext):
    await state.update_data(custom_name=message.text.strip())
    await message.answer("Send API endpoint URL.\nUse {key} for API key, {url} for URL.\nExample: https://mysite.com/api?api={key}&url={url}")
    await state.set_state(AdminStates.waiting_custom_endpoint)

@router.message(AdminStates.waiting_custom_endpoint)
async def custom_endpoint(message: Message, state: FSMContext):
    await state.update_data(custom_endpoint=message.text.strip())
    await message.answer("Send your API key:")
    await state.set_state(AdminStates.waiting_custom_key)

@router.message(AdminStates.waiting_custom_key)
async def custom_key(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    api_key = message.text.strip()
    name = data["custom_name"]
    endpoint = data["custom_endpoint"]
    test_ep = endpoint.replace("{key}", api_key).replace("{url}", "https://google.com")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(test_ep)
            if resp.status_code == 200:
                slug = name.lower().replace(" ", "")
                await upsert_shortener_config(slug, name, api_key, endpoint, "json_shortenedUrl")
                await message.answer(f"✅ {name} saved! Response: {resp.text[:100]}")
                return
        await message.answer("❌ API test failed.")
    except Exception as e:
        await message.answer(f"❌ Error: {str(e)[:100]}")

@router.callback_query(F.data == "admin_toggle_inject")
async def toggle_inject(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    cur = await get_setting("inject_links_enabled")
    new = "false" if cur == "true" else "true"
    await set_setting("inject_links_enabled", new)
    await callback.answer(f"Injection: {'✅ ON' if new=='true' else '❌ OFF'}", show_alert=True)

@router.callback_query(F.data == "admin_rotation")
async def rotation_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Round Robin", callback_data="admin_set_rot:round_robin")],
        [InlineKeyboardButton(text="🎲 Random", callback_data="admin_set_rot:random")],
        [InlineKeyboardButton(text="📊 Priority", callback_data="admin_set_rot:priority")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_shorteners")]])
    await callback.message.edit_text("Choose rotation mode:", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("admin_set_rot:"))
async def set_rotation(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    mode = callback.data.split(":")[1]
    await set_setting("shortener_rotation_mode", mode)
    await callback.answer(f"✅ Rotation: {mode}", show_alert=True)

@router.callback_query(F.data == "admin_test_apis")
async def test_apis(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    configs = await get_active_shortener_configs()
    if not configs:
        await callback.answer("No shorteners configured!", show_alert=True)
        return
    await callback.message.edit_text("🧪 Testing APIs...")
    text = "🧪 API Test Results:\n\n"
    for c in configs:
        try:
            ep = c["api_endpoint"].replace("{key}", c["api_key"]).replace("{url}", "https://google.com")
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(ep)
                ms = round(r.elapsed.total_seconds() * 1000)
                text += f"✅ {c['display_name']} — {r.status_code} ({ms}ms)\n"
        except Exception as e:
            text += f"❌ {c['display_name']} — {str(e)[:40]}\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="admin_shorteners")]])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


# ── Bypass Stats ──────────────────────────────────────────

@router.callback_query(F.data == "admin_bypass_stats")
async def bypass_stats_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    stats = await get_bypass_stats()
    text = f"🔓 Bypass Stats\n━━━━━━━━━━━━━━━━━━━━━━━━\n\nTotal: {stats['total']} | Success: {stats['success_rate']}%\n\nBy Method:\n"
    for m in stats['methods'][:10]:
        text += f"• {m['method']}: {m['cnt']}\n"
    text += "\nTop Shorteners:\n"
    for i, t in enumerate(stats['top_shorteners'][:10], 1):
        text += f"{i}. {t['shortener']}: {t['cnt']}\n"
    text += f"\nSupported: {get_total_count()}+"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu")]])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


# ── Revenue ───────────────────────────────────────────────

@router.callback_query(F.data == "admin_revenue")
async def revenue(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    db = await get_db()
    today = datetime.date.today().isoformat()
    today_inj = (await (await db.execute("SELECT COUNT(*) FROM bypass_history WHERE injected_url IS NOT NULL AND date(created_at)=?", (today,))).fetchone())[0]
    total_inj = (await (await db.execute("SELECT COUNT(*) FROM bypass_history WHERE injected_url IS NOT NULL")).fetchone())[0]
    cpm = 6
    text = (
        f"💰 Revenue Estimates\n━━━━━━━━━━━━━━━━\n\n"
        f"📊 Injected links:\n├── Today: {today_inj}\n└── Total: {total_inj}\n\n"
        f"💵 Est. revenue (~${cpm} CPM):\n├── Today: ~${round(today_inj * cpm / 1000, 2)}\n└── Total: ~${round(total_inj * cpm / 1000, 2)}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu")]])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


# ── API Health ────────────────────────────────────────────

@router.callback_query(F.data == "admin_api_health")
async def api_health(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    stats = await get_api_stats(24)
    text = "📈 API Health (24h)\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    if stats:
        for s in stats:
            text += f"🔹 {s['api_name']}: {s['total_calls']} calls, {s['success_rate']}% success, avg {s['avg_time_ms']}ms\n"
    else:
        text += "No API calls recorded yet.\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu")]])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


# ── Force Subscribe ───────────────────────────────────────

@router.callback_query(F.data == "admin_forcesub")
async def forcesub_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    enabled = await get_setting("force_sub_enabled")
    channels = await get_force_sub_channels()
    text = f"📢 Force Subscribe\n━━━━━━━━━━━━━━━━━━━━━\n\nStatus: {'✅ ON' if enabled=='true' else '❌ OFF'}\n\nChannels:\n"
    for c in channels:
        text += f"• {c['channel_username']}\n"
    if not channels:
        text += "None configured\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add Channel", callback_data="admin_add_channel")],
        [InlineKeyboardButton(text="🔛 Toggle", callback_data="admin_toggle_fsub")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu")]])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "admin_toggle_fsub")
async def toggle_fsub(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    cur = await get_setting("force_sub_enabled")
    new = "false" if cur == "true" else "true"
    await set_setting("force_sub_enabled", new)
    await callback.answer(f"Force Sub: {'✅ ON' if new=='true' else '❌ OFF'}", show_alert=True)

@router.callback_query(F.data == "admin_add_channel")
async def admin_add_channel(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await callback.message.edit_text("Send channel username (with @):")
    await state.set_state(AdminStates.waiting_channel)
    await callback.answer()

@router.message(AdminStates.waiting_channel)
async def process_channel(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id): return
    await state.clear()
    ch = message.text.strip()
    if not ch.startswith("@"):
        ch = "@" + ch
    try:
        chat = await bot.get_chat(ch)
        await add_force_sub_channel(ch, chat.id, chat.title)
        await message.answer(f"✅ {ch} added! Make sure bot is admin there.")
    except Exception as e:
        await message.answer(f"❌ Could not verify {ch}: {str(e)[:100]}")


# ── Broadcast ─────────────────────────────────────────────

@router.callback_query(F.data == "admin_broadcast")
async def broadcast_menu(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    total = await get_user_count()
    await callback.message.edit_text(f"📣 Broadcast\n\nSend your message. It will go to {total} users.")
    await state.set_state(AdminStates.waiting_broadcast)
    await callback.answer()

@router.message(AdminStates.waiting_broadcast)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id): return
    await state.clear()
    user_ids = await get_all_user_ids()
    sent = failed = 0
    progress = await message.answer(f"📣 Broadcasting to {len(user_ids)} users...")
    import asyncio
    for uid in user_ids:
        try:
            await bot.copy_message(chat_id=uid, from_chat_id=message.chat.id, message_id=message.message_id)
            sent += 1
        except:
            failed += 1
        if (sent + failed) % 25 == 0:
            await asyncio.sleep(1)
    await progress.edit_text(f"✅ Broadcast done! Sent: {sent} | Failed: {failed}")


# ── Settings ──────────────────────────────────────────────

@router.callback_query(F.data == "admin_settings")
async def settings_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    settings_list = [
        ("free_daily_limit", "🔢 Daily Limit"), ("cooldown_seconds", "⏰ Cooldown"),
        ("batch_limit_free", "📦 Batch Free"), ("batch_limit_premium", "📦 Batch Prem"),
        ("premium_stars_price", "⭐ Stars Price"), ("premium_stars_days", "⭐ Stars Days"),
        ("premium_referral_count", "👥 Ref Count"), ("premium_referral_days", "👥 Ref Days"),
        ("referral_bonus_credits", "🎁 Ref Bonus"),
    ]
    buttons = []
    for key, label in settings_list:
        val = await get_setting(key)
        buttons.append([InlineKeyboardButton(text=f"{label}: {val} ✏️", callback_data=f"admin_edit:{key}")])
    for key, label in [("premium_stars_enabled","⭐ Stars"),("premium_referral_enabled","👥 Referral"),
        ("inject_links_enabled","🔗 Injection"),("force_sub_enabled","📢 ForceSub"),("antispam_enabled","🛡️ AntiSpam"),
        ("cache_enabled","💾 Cache"),("maintenance_mode","🔧 Maintenance")]:
        val = await get_setting(key)
        st = "✅" if val == "true" else "❌"
        buttons.append([InlineKeyboardButton(text=f"{label}: {st} 🔛", callback_data=f"admin_toggle:{key}")])
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu")])
    await callback.message.edit_text("⚙️ Settings\n━━━━━━━━━━━━━━", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@router.callback_query(F.data.startswith("admin_edit:"))
async def edit_setting(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    key = callback.data.split(":")[1]
    val = await get_setting(key)
    await state.update_data(editing_key=key)
    await callback.message.edit_text(f"Current: {key} = {val}\nSend new value:")
    await state.set_state(AdminStates.waiting_setting_value)
    await callback.answer()

@router.message(AdminStates.waiting_setting_value)
async def process_setting(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    data = await state.get_data()
    await state.clear()
    key = data.get("editing_key")
    if key:
        old = await get_setting(key)
        await set_setting(key, message.text.strip())
        await message.answer(f"✅ {key}: {old} → {message.text.strip()}")

@router.callback_query(F.data.startswith("admin_toggle:"))
async def toggle_setting(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    key = callback.data.split(":")[1]
    cur = await get_setting(key)
    new = "false" if cur == "true" else "true"
    await set_setting(key, new)
    await callback.answer(f"{'✅ ON' if new=='true' else '❌ OFF'}", show_alert=True)

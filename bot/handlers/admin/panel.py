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

SHORTENER_PRESETS = {
    "shrinkme": {"name": "Shrinkme.io", "endpoint": "https://shrinkme.io/api?api={key}&url={url}", "format": "json_shortenedUrl"},
    "gplinks": {"name": "GPLinks.com", "endpoint": "https://gplinks.com/api?api={key}&url={url}", "format": "json_shortenedUrl"},
    "linkshortify": {"name": "Linkshortify", "endpoint": "https://linkshortify.com/api?api={key}&url={url}", "format": "json_shortenedUrl"},
    "arolinks": {"name": "AroLinks", "endpoint": "https://arolinks.com/api?api={key}&url={url}", "format": "json_shortenedUrl"},
    "ouo": {"name": "OUO.io", "endpoint": "https://ouo.io/api/{key}?s={url}", "format": "plain_text"},
    "exeio": {"name": "Exe.io", "endpoint": "https://exe.io/api?api={key}&url={url}", "format": "json_shortenedUrl"},
    "fclc": {"name": "FC.lc", "endpoint": "https://fc.lc/api?api={key}&url={url}", "format": "json_shortenedUrl"},
    "shortest": {"name": "Shorte.st", "endpoint": "https://api.shorte.st/v1/data/url", "format": "json_shortenedUrl"},
}

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
        f"👥 Users:\n├── Total: {total}\n├── New today: {new_today}\n├── Premium: {premium}\n└── Banned: {banned}\n\n"
        f"🔓 Bypasses:\n├── Today: {bypasses_today}\n└── Total: {total_bypasses}\n\n"
        f"🔗 APIs: {len(configs)} active | 🤖 Uptime: {h}h {m}m")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Refresh", callback_data="admin_dashboard"),
         InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu")]])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "admin_users")
async def users_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    db = await get_db()
    total = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Find User by ID", callback_data="admin_find_user")],
        [InlineKeyboardButton(text="📋 Top 10 Users", callback_data="admin_top_users")],
        [InlineKeyboardButton(text="🆕 Recent 20", callback_data="admin_recent_users")],
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
    except:
        await message.answer("Invalid ID.")
        return
    db = await get_db()
    row = await (await db.execute("SELECT * FROM users WHERE user_id=?", (uid,))).fetchone()
    if not row:
        await message.answer("User not found.")
        return
    u = dict(row)
    status = "⭐ Premium" if u["is_premium"] else "🆓 Free"
    text = (f"👤 {u.get('full_name','')} (@{u.get('username','')})\nID: {uid}\n"
        f"Status: {status}\nBypasses: {u.get('total_bypasses',0)}\nReferrals: {u.get('total_referrals',0)}\n"
        f"Banned: {'Yes' if u.get('is_banned') else 'No'}")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👑 Give Premium 30d", callback_data=f"admin_give_prem:{uid}"),
         InlineKeyboardButton(text="🚫 Toggle Ban", callback_data=f"admin_toggle_ban:{uid}")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_users")]])
    await message.answer(text, reply_markup=kb)

@router.callback_query(F.data.startswith("admin_give_prem:"))
async def give_premium(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    uid = int(callback.data.split(":")[1])
    db = await get_db()
    until = (datetime.datetime.now() + datetime.timedelta(days=30)).isoformat()
    await db.execute("UPDATE users SET is_premium=1, premium_until=? WHERE user_id=?", (until, uid))
    await db.commit()
    await callback.answer("✅ Premium granted for 30 days!", show_alert=True)

@router.callback_query(F.data.startswith("admin_toggle_ban:"))
async def toggle_ban(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    uid = int(callback.data.split(":")[1])
    db = await get_db()
    row = await (await db.execute("SELECT is_banned FROM users WHERE user_id=?", (uid,))).fetchone()
    new_val = 0 if row and row[0] else 1
    await db.execute("UPDATE users SET is_banned=? WHERE user_id=?", (new_val, uid))
    await db.commit()
    await callback.answer(f"{'🚫 Banned' if new_val else '✅ Unbanned'}", show_alert=True)

@router.callback_query(F.data == "admin_top_users")
async def top_users(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    db = await get_db()
    rows = await (await db.execute("SELECT user_id, full_name, total_bypasses FROM users ORDER BY total_bypasses DESC LIMIT 10")).fetchall()
    text = "📋 Top 10 Users:\n\n"
    for i, r in enumerate(rows, 1):
        text += f"{i}. {r['full_name'] or r['user_id']} — {r['total_bypasses']} bypasses\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="admin_users")]])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "admin_recent_users")
async def recent_users(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    db = await get_db()
    rows = await (await db.execute("SELECT user_id, full_name, joined_at FROM users ORDER BY joined_at DESC LIMIT 20")).fetchall()
    text = "🆕 Recent Users:\n\n"
    for r in rows:
        text += f"• {r['full_name'] or r['user_id']} — {r['joined_at'][:10]}\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="admin_users")]])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "admin_shorteners")
async def shorteners_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    db = await get_db()
    configs = await (await db.execute("SELECT * FROM shortener_configs ORDER BY priority")).fetchall()
    inject = await get_setting("inject_links_enabled")
    rotation = await get_setting("shortener_rotation_mode")
    text = "🔗 Your Shortener APIs\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    if configs:
        for i, c in enumerate(configs, 1):
            st = "✅" if c["is_active"] else "❌"
            text += f"{i}. {st} {c['display_name']} — {c['total_links_created']} links\n"
    else:
        text += "No shorteners configured yet.\n"
    text += f"\nRotation: {rotation} | Injection: {'✅' if inject=='true' else '❌'}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add Shortener", callback_data="admin_add_shortener")],
        [InlineKeyboardButton(text="🔄 Rotation Mode", callback_data="admin_rotation"),
         InlineKeyboardButton(text="🔛 Toggle Injection", callback_data="admin_toggle_inject")],
        [InlineKeyboardButton(text="🧪 Test All APIs", callback_data="admin_test_apis")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu")]])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "admin_add_shortener")
async def add_shortener(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    buttons = []
    row = []
    for key, val in SHORTENER_PRESETS.items():
        row.append(InlineKeyboardButton(text=val["name"], callback_data=f"admin_cfg_short:{key}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="🔧 Custom Shortener", callback_data="admin_custom_short")])
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="admin_shorteners")])
    await callback.message.edit_text("Choose shortener to configure:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@router.callback_query(F.data.startswith("admin_cfg_short:"))
async def cfg_shortener(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    key = callback.data.split(":")[1]
    preset = SHORTENER_PRESETS.get(key)
    if not preset:
        await callback.answer("Unknown shortener")
        return
    await state.update_data(short_key=key, short_preset=preset)
    await callback.message.edit_text(f"🔗 {preset['name']}\n\nAPI: {preset['endpoint']}\n\nSend your API key:")
    await state.set_state(AdminStates.waiting_shortener_key)
    await callback.answer()

@router.message(AdminStates.waiting_shortener_key)
async def process_shortener_key(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    data = await state.get_data()
    await state.clear()
    api_key = message.text.strip()
    preset = data.get("short_preset", {})
    name = preset.get("name", "Custom")
    endpoint = preset.get("endpoint", "")
    fmt = preset.get("format", "json_shortenedUrl")
    # Test the API
    test_url = "https://google.com"
    test_endpoint = endpoint.replace("{key}", api_key).replace("{url}", test_url)
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(test_endpoint)
            if resp.status_code == 200:
                result_data = resp.json() if fmt != "plain_text" else {"shortenedUrl": resp.text.strip()}
                short = result_data.get("shortenedUrl") or result_data.get("short_url") or resp.text.strip()
                if short and short.startswith("http"):
                    db = await get_db()
                    await db.execute(
                        "INSERT OR REPLACE INTO shortener_configs (shortener_name, display_name, api_key, api_endpoint, api_format, is_active, total_links_created, priority) VALUES (?,?,?,?,?,1,0,5)",
                        (data.get("short_key", name.lower()), name, api_key, endpoint, fmt))
                    await db.commit()
                    await message.answer(f"✅ {name} configured and verified!\nTest: {short}")
                    return
            await message.answer(f"❌ API test failed (status {resp.status_code}). Check your key.")
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
    await message.answer("Send API endpoint URL.\nUse {key} for API key and {url} for the URL.\nExample: https://mysite.com/api?api={key}&url={url}")
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
    test_url = "https://google.com"
    test_ep = endpoint.replace("{key}", api_key).replace("{url}", test_url)
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(test_ep)
            if resp.status_code == 200:
                db = await get_db()
                await db.execute(
                    "INSERT OR REPLACE INTO shortener_configs (shortener_name, display_name, api_key, api_endpoint, api_format, is_active, total_links_created, priority) VALUES (?,?,?,?,?,1,0,5)",
                    (name.lower().replace(" ",""), name, api_key, endpoint, "json_shortenedUrl"))
                await db.commit()
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
    db = await get_db()
    configs = await (await db.execute("SELECT * FROM shortener_configs WHERE is_active=1")).fetchall()
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
                text += f"✅ {c['display_name']} — {r.status_code} ({round(r.elapsed.total_seconds(),1)}s)\n"
        except Exception as e:
            text += f"❌ {c['display_name']} — {str(e)[:40]}\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="admin_shorteners")]])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "admin_forcesub")
async def forcesub_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    db = await get_db()
    enabled = await get_setting("force_sub_enabled")
    channels = await (await db.execute("SELECT * FROM force_sub_channels WHERE is_active=1")).fetchall()
    text = f"📢 Force Subscribe\n━━━━━━━━━━━━━━━━━━━━━\n\nStatus: {'✅ ON' if enabled=='true' else '❌ OFF'}\n\nChannels:\n"
    for c in channels:
        text += f"• {c['channel_username']}\n"
    if not channels:
        text += "None configured\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add Channel", callback_data="admin_add_channel")],
        [InlineKeyboardButton(text="🔛 Toggle Force Sub", callback_data="admin_toggle_fsub")],
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
async def add_channel(callback: CallbackQuery, state: FSMContext):
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
        db = await get_db()
        await db.execute("INSERT OR IGNORE INTO force_sub_channels (channel_username, channel_id) VALUES (?,?)", (ch, chat.id))
        await db.commit()
        await message.answer(f"✅ {ch} added! Make sure bot is admin there.")
    except Exception as e:
        await message.answer(f"❌ Could not verify {ch}: {str(e)[:100]}")

@router.callback_query(F.data == "admin_revenue")
async def revenue(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    db = await get_db()
    today = datetime.date.today().isoformat()
    today_links = (await (await db.execute("SELECT COUNT(*) FROM bypass_history WHERE injected_url IS NOT NULL AND date(created_at)=?", (today,))).fetchone())[0]
    total_links = (await (await db.execute("SELECT COUNT(*) FROM bypass_history WHERE injected_url IS NOT NULL")).fetchone())[0]
    cpm = 6
    today_rev = round(today_links * cpm / 1000, 2)
    total_rev = round(total_links * cpm / 1000, 2)
    text = (f"💰 Revenue Estimates\n━━━━━━━━━━━━━━━━\n\n"
        f"📊 Links created:\n├── Today: {today_links}\n└── Total: {total_links}\n\n"
        f"💵 Est. revenue (avg $6 CPM):\n├── Today: ~${today_rev}\n└── Total: ~${total_rev}")
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu")]])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "admin_bypass_stats")
async def bypass_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    db = await get_db()
    total = (await (await db.execute("SELECT COUNT(*) FROM bypass_history")).fetchone())[0]
    methods = await (await db.execute("SELECT bypass_method, COUNT(*) as cnt FROM bypass_history GROUP BY bypass_method ORDER BY cnt DESC")).fetchall()
    top = await (await db.execute("SELECT shortener_detected, COUNT(*) as cnt FROM bypass_history GROUP BY shortener_detected ORDER BY cnt DESC LIMIT 10")).fetchall()
    text = f"🔓 Bypass Stats\n━━━━━━━━━━━━━━━━━━━━━━━━\n\nTotal: {total}\n\nBy Method:\n"
    for m in methods:
        text += f"• {m['bypass_method']}: {m['cnt']}\n"
    text += "\nTop Shorteners:\n"
    for i, t in enumerate(top, 1):
        text += f"{i}. {t['shortener_detected']}: {t['cnt']}\n"
    text += f"\nSupported: {len(KNOWN_SHORTENER_DOMAINS)}+"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu")]])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "admin_broadcast")
async def broadcast_menu(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    total = await get_user_count()
    await callback.message.edit_text(f"📣 Broadcast\n\nSend your message now. It will go to {total} users.")
    await state.set_state(AdminStates.waiting_broadcast)
    await callback.answer()

@router.message(AdminStates.waiting_broadcast)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id): return
    await state.clear()
    user_ids = await get_all_user_ids()
    sent = failed = 0
    progress = await message.answer(f"📣 Broadcasting to {len(user_ids)} users...")
    for uid in user_ids:
        try:
            await bot.copy_message(chat_id=uid, from_chat_id=message.chat.id, message_id=message.message_id)
            sent += 1
        except:
            failed += 1
        if (sent + failed) % 25 == 0:
            import asyncio
            await asyncio.sleep(1)
    await progress.edit_text(f"✅ Broadcast complete! Sent: {sent} | Failed: {failed}")

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
        ("inject_links_enabled","🔗 Injection"),("force_sub_enabled","📢 ForceSub"),("antispam_enabled","🛡️ AntiSpam")]:
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

@router.callback_query(F.data == "back_start")
async def back_start(callback: CallbackQuery):
    await callback.message.edit_text("Use /start to go back.")
    await callback.answer()

@router.callback_query(F.data == "share_bot")
async def share_bot(callback: CallbackQuery, bot: Bot):
    me = await bot.get_me()
    await callback.answer(f"Share: https://t.me/{me.username}", show_alert=True)

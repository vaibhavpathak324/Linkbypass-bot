from bot.database.db import get_setting, get_db

async def get_active_force_sub_channels():
    db = await get_db()
    cur = await db.execute("SELECT * FROM force_sub_channels WHERE is_active=1")
    return [dict(r) for r in await cur.fetchall()]

async def check_force_sub(user_id, bot):
    enabled = await get_setting("force_sub_enabled")
    if enabled != "true":
        return {"passed": True, "missing": []}
    channels = await get_active_force_sub_channels()
    if not channels:
        return {"passed": True, "missing": []}
    missing = []
    for ch in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch["channel_username"], user_id=user_id)
            if member.status in ("left", "kicked"):
                missing.append(ch["channel_username"])
        except:
            missing.append(ch["channel_username"])
    return {"passed": len(missing) == 0, "missing": missing}

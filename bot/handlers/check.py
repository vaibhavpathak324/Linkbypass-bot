"""
LinkBypass Pro — Check Handler
"""
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command, CommandObject
from bot.engine.url_utils import detect_shortener, is_valid_url, extract_urls, get_domain
from bot.engine.domain_list import get_shortener_info

router = Router()

@router.message(Command("check"))
async def cmd_check(message: Message, command: CommandObject):
    if not command.args:
        await message.answer("Usage: /check <url>\nExample: /check https://shrinkme.io/XXXX")
        return
    url = command.args.strip()
    urls = extract_urls(url)
    if not urls:
        if not url.startswith('http'):
            url = 'https://' + url
        urls = [url]
    url = urls[0]
    if not is_valid_url(url):
        await message.answer("❌ Invalid URL.")
        return
    domain = get_domain(url)
    info = get_shortener_info(domain)
    name, category = detect_shortener(url)
    if info:
        await message.answer(
            f"✅ Supported Shortener!\n\n"
            f"🏷 Name: {info['name']}\n"
            f"🌐 Domain: {domain}\n"
            f"📂 Category: {info.get('category', 'general')}\n"
            f"⚙️ Method: {info.get('method', 'auto')}\n"
            f"📦 Module: {info.get('module', 'generic')}\n\n"
            f"Send the link to bypass it!"
        )
    else:
        await message.answer(
            f"❓ Unknown Shortener\n\n"
            f"🌐 Domain: {domain}\n\n"
            f"This domain isn't in our database, but I'll still try to bypass it using generic methods. Send the link!"
        )

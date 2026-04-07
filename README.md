# LinkBypass Pro Bot 🔓

A powerful Telegram bot that bypasses 500+ URL shorteners instantly.

## Features
- 🔓 5-layer bypass engine
- 📊 500+ supported shorteners
- ⚡ Smart caching
- 💰 Admin monetization (link injection)
- ⭐ Premium via Telegram Stars
- 👥 Referral system
- 📢 Force subscribe
- 📣 Broadcasting
- 🌐 Multi-language (EN, HI)

## Architecture
- Layer 1: HTTP redirect following
- Layer 2: Site-specific pattern extraction
- Layer 3: External bypass APIs (linkbypass.lol, bypass.vip, etc.)
- Layer 4: Cloudscraper (JS challenge handling)
- Layer 5: Advanced headless techniques

## Deploy on Render
1. Fork this repo
2. Create a new Web Service on Render
3. Set environment variables: `BOT_TOKEN`, `ADMIN_USER_ID`
4. Deploy!

## Tech Stack
- Python 3.11 + aiogram 3.x
- aiosqlite for async database
- httpx + curl_cffi for HTTP requests
- cloudscraper for anti-bot bypass
- aiohttp for health check web server

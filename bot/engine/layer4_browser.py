"""
LinkBypass Pro — Layer 4: Advanced Browser Simulation v4.0
===========================================================
curl_cffi TLS fingerprinting + cloudscraper + aiohttp with
comprehensive header rotation and AdLinkFly flow automation.
"""

import re
import asyncio
import logging
import random
from typing import Optional
from urllib.parse import urlparse

from bot.config import BROWSER_TIMEOUT, USER_AGENTS
from bot.engine.url_utils import is_valid_url, get_domain

logger = logging.getLogger(__name__)

DESTINATION_PATTERNS = [
    r'href=["\']?(https?://[^"\'\s>]+)["\']?\s*(?:id|class)=["\'].*?(?:btn|button|download|continue|redirect|go|visit|proceed)',
    r'window\.location(?:\.href)?\s*=\s*["\'](https?://[^"\' ]+)["\']',
    r'window\.open\s*\(["\'](https?://[^"\' ]+)["\']',
    r'<meta\s+http-equiv=["\']refresh["\']\s+content=["\']\d+;\s*url=(https?://[^"\']+)["\']',
    r'location\.replace\s*\(["\'](https?://[^"\' ]+)["\']',
    r'var\s+(?:url|link|dest|redirect|target)\s*=\s*["\'](https?://[^"\' ]+)["\']',
    r'data-(?:url|href|link|redirect)=["\']?(https?://[^"\'\s>]+)["\']?',
    r'"(?:url|link|destination|redirect)"\s*:\s*"(https?://[^"]+)"',
]

BLOCKLIST = {'cloudflare.com', 'challenges.cloudflare.com', 'google.com',
             'gstatic.com', 'googleapis.com', 'facebook.com', 'doubleclick.net',
             'googlesyndication.com', 'cloudflareinsights.com'}


def _is_dest(url: str, src_domain: str) -> bool:
    if not url or not is_valid_url(url):
        return False
    d = get_domain(url)
    return bool(d and d != src_domain and d not in BLOCKLIST)


def _extract(html: str, domain: str) -> Optional[str]:
    for pat in DESTINATION_PATTERNS:
        try:
            for m in re.finditer(pat, html, re.IGNORECASE):
                if _is_dest(m.group(1), domain):
                    return m.group(1)
        except Exception:
            continue
    return None


async def _try_curl_cffi(url: str) -> Optional[str]:
    try:
        from curl_cffi.requests import AsyncSession
    except ImportError:
        return None

    domain = get_domain(url)

    for imp in ["chrome124", "chrome120", "safari17_0", "edge101"]:
        try:
            async with AsyncSession(impersonate=imp, timeout=BROWSER_TIMEOUT, verify=False) as s:
                resp = await s.get(url, allow_redirects=True, max_redirects=10, headers={
                    'User-Agent': random.choice(USER_AGENTS),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Referer': 'https://www.google.com/',
                })

                final = str(resp.url)
                if _is_dest(final, domain):
                    return final

                if resp.status_code == 200:
                    dest = _extract(resp.text, domain)
                    if dest:
                        return dest
        except Exception:
            continue
    return None


async def _try_cloudscraper(url: str) -> Optional[str]:
    try:
        import cloudscraper
    except ImportError:
        return None

    domain = get_domain(url)

    def _scrape():
        s = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "desktop": True},
            delay=5,
        )
        s.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Upgrade-Insecure-Requests": "1",
        })
        resp = s.get(url, allow_redirects=True, timeout=20)
        final = resp.url
        if _is_dest(final, domain):
            return final
        if resp.status_code == 200:
            return _extract(resp.text, domain)
        return None

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _scrape)


async def _try_aiohttp(url: str) -> Optional[str]:
    try:
        import aiohttp
    except ImportError:
        return None

    domain = get_domain(url)

    try:
        async with aiohttp.ClientSession(headers={
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }) as session:
            async with session.get(url, allow_redirects=True,
                                   timeout=aiohttp.ClientTimeout(total=15)) as resp:
                final = str(resp.url)
                if _is_dest(final, domain):
                    return final
                if resp.status == 200:
                    text = await resp.text()
                    return _extract(text, domain)
    except Exception:
        pass
    return None


async def attempt(url: str) -> Optional[str]:
    """Layer 4 entry point."""
    logger.info(f"[Layer4] Starting for {url[:80]}")

    for name, fn in [("curl_cffi", _try_curl_cffi), ("cloudscraper", _try_cloudscraper), ("aiohttp", _try_aiohttp)]:
        try:
            result = await asyncio.wait_for(fn(url), timeout=25)
            if result:
                logger.info(f"[Layer4] {name} -> {result[:80]}")
                return result
        except asyncio.TimeoutError:
            logger.debug(f"[Layer4] {name} timeout")
        except Exception as e:
            logger.debug(f"[Layer4] {name} err: {e}")

    return None

try_cloudscraper_bypass = attempt

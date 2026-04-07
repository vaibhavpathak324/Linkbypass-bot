"""
LinkBypass Pro — Shorte.st Bypass Pattern
===========================================
Shorte.st uses JavaScript obfuscation to hide the destination URL.
The URL is encoded and decoded via JavaScript at runtime.
"""

import re
import json
import logging
import random
from typing import Optional

import httpx

from bot.config import USER_AGENTS
from bot.engine.url_utils import is_valid_url, get_domain, try_base64_decode

logger = logging.getLogger(__name__)


async def bypass(url: str) -> Optional[str]:
    """Bypass a Shorte.st family URL."""
    logger.info(f"[Shortest] Bypassing: {url[:80]}")
    domain = get_domain(url)

    try:
        async with httpx.AsyncClient(timeout=15, verify=False, follow_redirects=True) as client:
            resp = await client.get(url, headers={
                'User-Agent': random.choice(USER_AGENTS),
                'Accept': 'text/html',
                'Referer': 'https://www.google.com/',
            })

            if resp.status_code != 200:
                return None

            html = resp.text

            # Method 1: Look for the destination URL pattern
            dest_patterns = [
                r'var\s+nextUrl\s*=\s*["\']([^"\']+)["\']',
                r'var\s+destinationUrl\s*=\s*["\']([^"\']+)["\']',
                r'"destinationUrl"\s*:\s*"([^"]+)"',
                r'"nextUrl"\s*:\s*"([^"]+)"',
                r'<a[^>]*id=["\']?skip["\']?[^>]*href=["\']([^"\']+)["\']',
                r'<a[^>]*href=["\']([^"\']+)["\'][^>]*id=["\']?skip["\']?',
            ]

            for pat in dest_patterns:
                m = re.search(pat, html, re.IGNORECASE)
                if m:
                    found = m.group(1).replace('\\/', '/')
                    if is_valid_url(found) and get_domain(found) != domain:
                        logger.info(f"[Shortest] Found URL: {found[:80]}")
                        return found

            # Method 2: Look for timer-based redirect
            timer_url_match = re.search(
                r'(?:setTimeout|setInterval)\s*\(\s*function[^{]*\{[^}]*(?:window\.)?location[^=]*=\s*["\']([^"\']+)',
                html, re.IGNORECASE | re.DOTALL
            )
            if timer_url_match:
                found = timer_url_match.group(1)
                if is_valid_url(found) and get_domain(found) != domain:
                    return found

            # Method 3: Base64 decode any encoded strings
            for m in re.finditer(r'["\']([A-Za-z0-9+/]{30,}={0,2})["\']', html):
                decoded = try_base64_decode(m.group(1))
                if decoded and get_domain(decoded) != domain:
                    return decoded

    except Exception as e:
        logger.debug(f"[Shortest] Error: {e}")

    return None

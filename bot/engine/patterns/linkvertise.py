"""
LinkBypass Pro — Linkvertise Bypass Pattern
=============================================
Linkvertise is a heavily protected shortener. Best bypassed
via external APIs since it uses advanced anti-bot measures.
"""

import re
import json
import logging
import random
from typing import Optional
from urllib.parse import urlparse, quote

import httpx

from bot.config import PATTERN_TIMEOUT, USER_AGENTS
from bot.engine.url_utils import is_valid_url, get_domain, try_base64_decode

logger = logging.getLogger(__name__)


async def bypass(url: str) -> Optional[str]:
    """Bypass a Linkvertise URL."""
    logger.info(f"[Linkvertise] Bypassing: {url[:80]}")
    domain = get_domain(url)

    # Method 1: Try thebypasser.com API
    result = await _try_thebypasser(url)
    if result:
        return result

    # Method 2: Try bypass.vip API
    result = await _try_bypass_vip(url)
    if result:
        return result

    # Method 3: Try direct extraction
    result = await _try_direct(url, domain)
    if result:
        return result

    return None


async def _try_thebypasser(url: str) -> Optional[str]:
    """Try thebypasser.com Linkvertise bypass."""
    try:
        async with httpx.AsyncClient(timeout=20, verify=False) as client:
            resp = await client.post(
                "https://api.bypass.vip/bypass",
                json={"url": url},
                headers={
                    'User-Agent': random.choice(USER_AGENTS),
                    'Accept': 'application/json',
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                result = data.get('destination') or data.get('result') or data.get('bypassed')
                if result and is_valid_url(str(result)):
                    logger.info(f"[Linkvertise] thebypasser success: {result[:80]}")
                    return str(result)
    except Exception as e:
        logger.debug(f"[Linkvertise] thebypasser error: {e}")
    return None


async def _try_bypass_vip(url: str) -> Optional[str]:
    """Try bypass.vip API."""
    try:
        async with httpx.AsyncClient(timeout=20, verify=False) as client:
            resp = await client.get(
                f"https://bypass.vip/bypass?url={quote(url)}",
                headers={'User-Agent': random.choice(USER_AGENTS)}
            )
            if resp.status_code == 200:
                data = resp.json()
                result = data.get('destination') or data.get('url')
                if result and is_valid_url(str(result)):
                    return str(result)
    except Exception:
        pass
    return None


async def _try_direct(url: str, domain: str) -> Optional[str]:
    """Try direct extraction from Linkvertise page."""
    try:
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            resp = await client.get(url, headers={
                'User-Agent': random.choice(USER_AGENTS),
                'Accept': 'text/html',
            })
            if resp.status_code != 200:
                return None

            html = resp.text

            # Look for the target URL in page data
            patterns = [
                r'"target"\s*:\s*"([^"]+)"',
                r'"url"\s*:\s*"([^"]+)"',
                r'data-target=["\']([^"\']+)["\']',
            ]
            for pat in patterns:
                m = re.search(pat, html)
                if m:
                    found = m.group(1).replace('\\/', '/')
                    if is_valid_url(found) and get_domain(found) != domain:
                        return found

            # Check for base64 encoded target
            b64_match = re.search(r'"target_b64"\s*:\s*"([^"]+)"', html)
            if b64_match:
                decoded = try_base64_decode(b64_match.group(1))
                if decoded:
                    return decoded

    except Exception as e:
        logger.debug(f"[Linkvertise] direct error: {e}")
    return None

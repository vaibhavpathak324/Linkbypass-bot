"""
LinkBypass Pro — HubCloud Bypass Pattern
==========================================
HubCloud stores files and provides download links.
"""

import re
import logging
import random
from typing import Optional
from urllib.parse import urljoin

import httpx

from bot.config import USER_AGENTS
from bot.engine.url_utils import is_valid_url, get_domain

logger = logging.getLogger(__name__)


async def bypass(url: str) -> Optional[str]:
    """Bypass a HubCloud URL to get direct download."""
    logger.info(f"[HubCloud] Bypassing: {url[:80]}")
    domain = get_domain(url)

    try:
        async with httpx.AsyncClient(timeout=20, verify=False, follow_redirects=True) as client:
            resp = await client.get(url, headers={
                'User-Agent': random.choice(USER_AGENTS),
                'Accept': 'text/html',
                'Referer': 'https://www.google.com/',
            })

            if resp.status_code != 200:
                return None

            html = resp.text

            # Look for download/direct link
            patterns = [
                r'href=["\']([^"\']*(?:drive\.google|mega\.nz|mediafire|gofile|pixeldrain)[^"\']*)["\']',
                r'href=["\']([^"\']+)["\'][^>]*>\s*(?:Download|Direct|Server|Fast)[^<]*<',
                r'<a[^>]*class=["\'][^"\']*(?:btn|download)[^"\']*["\'][^>]*href=["\']([^"\']+)["\']',
                r'window\.open\(["\']([^"\']+)["\']',
                r'var\s+(?:url|link|download)\s*=\s*["\']([^"\']+)["\']',
            ]

            for pat in patterns:
                for m in re.finditer(pat, html, re.IGNORECASE):
                    found = m.group(1)
                    if not found.startswith('http'):
                        found = urljoin(url, found)
                    if is_valid_url(found) and get_domain(found) != domain:
                        logger.info(f"[HubCloud] Found link: {found[:80]}")
                        return found

    except Exception as e:
        logger.debug(f"[HubCloud] Error: {e}")

    return None

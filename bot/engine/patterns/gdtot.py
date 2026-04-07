"""
LinkBypass Pro — GDTot Bypass Pattern
=======================================
GDTot provides Google Drive download links.
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
    """Bypass a GDTot URL."""
    logger.info(f"[GDTot] Bypassing: {url[:80]}")
    domain = get_domain(url)

    try:
        async with httpx.AsyncClient(timeout=20, verify=False, follow_redirects=True) as client:
            resp = await client.get(url, headers={
                'User-Agent': random.choice(USER_AGENTS),
                'Accept': 'text/html',
            })

            if resp.status_code != 200:
                return None

            html = resp.text

            # GDTot patterns
            patterns = [
                r'href=["\']([^"\']*drive\.google\.com[^"\']*)["\']',
                r'href=["\']([^"\']+)["\'][^>]*>\s*(?:Download|Direct|Click)[^<]*<',
                r'window\.open\(["\']([^"\']+)["\']',
                r'var\s+(?:url|link)\s*=\s*["\']([^"\']+)["\']',
                r'data-(?:url|link)\s*=\s*["\']([^"\']+)["\']',
            ]

            for pat in patterns:
                for m in re.finditer(pat, html, re.IGNORECASE):
                    found = m.group(1)
                    if not found.startswith('http'):
                        found = urljoin(url, found)
                    if is_valid_url(found) and get_domain(found) != domain:
                        return found

    except Exception as e:
        logger.debug(f"[GDTot] Error: {e}")

    return None

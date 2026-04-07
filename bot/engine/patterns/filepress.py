"""
LinkBypass Pro — FilePress Bypass Pattern
===========================================
FilePress provides file hosting with ad-wall.
"""

import re
import json
import logging
import random
from typing import Optional
from urllib.parse import urljoin

import httpx

from bot.config import USER_AGENTS
from bot.engine.url_utils import is_valid_url, get_domain, extract_hidden_inputs

logger = logging.getLogger(__name__)


async def bypass(url: str) -> Optional[str]:
    """Bypass a FilePress URL."""
    logger.info(f"[FilePress] Bypassing: {url[:80]}")
    domain = get_domain(url)

    try:
        async with httpx.AsyncClient(timeout=20, verify=False) as client:
            resp = await client.get(url, headers={
                'User-Agent': random.choice(USER_AGENTS),
                'Accept': 'text/html',
            }, follow_redirects=True)

            if resp.status_code != 200:
                return None

            html = resp.text

            # Look for file download link
            patterns = [
                r'href=["\']([^"\']+)["\'][^>]*>\s*(?:Download|Direct|Get File)[^<]*<',
                r'<a[^>]*class=["\'][^"\']*(?:download|btn-success)[^"\']*["\'][^>]*href=["\']([^"\']+)["\']',
                r'window\.location\s*=\s*["\']([^"\']+)["\']',
            ]

            for pat in patterns:
                m = re.search(pat, html, re.IGNORECASE)
                if m:
                    found = m.group(1)
                    if not found.startswith('http'):
                        found = urljoin(url, found)
                    if is_valid_url(found) and get_domain(found) != domain:
                        return found

            # Try form submission
            inputs = extract_hidden_inputs(html)
            if inputs:
                form_resp = await client.post(
                    str(resp.url), data=inputs,
                    headers={'Referer': str(resp.url)},
                    follow_redirects=True
                )
                final = str(form_resp.url)
                if get_domain(final) != domain and is_valid_url(final):
                    return final

    except Exception as e:
        logger.debug(f"[FilePress] Error: {e}")

    return None

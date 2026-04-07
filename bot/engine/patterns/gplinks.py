"""
LinkBypass Pro — GPLinks Bypass Pattern
=========================================
GPLinks is a popular Indian URL shortener based on AdLinkFly
with some custom modifications. Uses a specific /links/go endpoint.
"""

import re
import logging
from typing import Optional

import httpx

from bot.engine.patterns.adlinkfly import bypass as adlinkfly_bypass

logger = logging.getLogger(__name__)


async def bypass(url: str) -> Optional[str]:
    """Bypass a GPLinks URL. Delegates to AdLinkFly with GP-specific tweaks."""
    logger.info(f"[GPLinks] Bypassing: {url[:80]}")

    # GPLinks is AdLinkFly-based, so use the AdLinkFly bypass
    result = await adlinkfly_bypass(url)
    if result:
        return result

    # GPLinks-specific: try direct API
    try:
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            # Some GPLinks instances have a JSON API
            resp = await client.get(
                url,
                headers={
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                },
            )
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    if 'url' in data:
                        return data['url']
                except Exception:
                    pass
    except Exception as e:
        logger.debug(f"[GPLinks] API attempt error: {e}")

    return None

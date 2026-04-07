"""
LinkBypass Pro — ShareUs.io Bypass Pattern
============================================
ShareUs is AdLinkFly-based with some custom modifications.
Uses token extraction and form POST similar to AdLinkFly.
"""

import re
import json
import logging
from typing import Optional

import httpx

from bot.engine.patterns.adlinkfly import bypass as adlinkfly_bypass
from bot.engine.url_utils import is_valid_url, get_domain

logger = logging.getLogger(__name__)


async def bypass(url: str) -> Optional[str]:
    """Bypass a ShareUs URL."""
    logger.info(f"[ShareUs] Bypassing: {url[:80]}")

    # ShareUs is AdLinkFly-based
    result = await adlinkfly_bypass(url)
    if result:
        return result

    # ShareUs-specific: Try the API endpoint
    try:
        domain = get_domain(url)
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            # Extract the alias
            path = url.rstrip('/').split('/')[-1]

            # Try shareus-specific go endpoint
            resp = await client.post(
                f"https://{domain}/links/go",
                data={'alias': path, '_token': ''},
                headers={
                    'X-Requested-With': 'XMLHttpRequest',
                    'Referer': url,
                }
            )
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    dest = data.get('url') or data.get('destination')
                    if dest and is_valid_url(str(dest)):
                        return str(dest)
                except Exception:
                    pass
    except Exception as e:
        logger.debug(f"[ShareUs] API error: {e}")

    return None

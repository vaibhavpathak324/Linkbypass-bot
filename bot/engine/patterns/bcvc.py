"""
LinkBypass Pro — BC.VC Bypass Pattern
=======================================
BC.VC is a multi-step ad shortener.
"""

import re
import logging
import random
from typing import Optional

import httpx

from bot.config import USER_AGENTS
from bot.engine.url_utils import is_valid_url, get_domain, extract_hidden_inputs

logger = logging.getLogger(__name__)


async def bypass(url: str) -> Optional[str]:
    """Bypass a BC.VC URL."""
    logger.info(f"[BCVC] Bypassing: {url[:80]}")
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

            # BC.VC stores the URL in a JavaScript variable
            url_match = re.search(r'var\s+url\s*=\s*["\']([^"\']+)["\']', html)
            if url_match:
                found = url_match.group(1)
                if is_valid_url(found) and get_domain(found) != domain:
                    return found

            # Try form submission
            inputs = extract_hidden_inputs(html)
            if inputs:
                form_url = f"https://{domain}/fly/links/fly"
                form_resp = await client.post(form_url, data=inputs, headers={
                    'User-Agent': random.choice(USER_AGENTS),
                    'Referer': url,
                })
                final = str(form_resp.url)
                if get_domain(final) != domain and is_valid_url(final):
                    return final

    except Exception as e:
        logger.debug(f"[BCVC] Error: {e}")

    return None

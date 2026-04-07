"""
LinkBypass Pro — MDisk Bypass Pattern
=======================================
MDisk.me uses an API to get direct download links.
"""

import re
import json
import logging
import random
from typing import Optional
from urllib.parse import urlparse

import httpx

from bot.config import USER_AGENTS
from bot.engine.url_utils import is_valid_url, get_domain

logger = logging.getLogger(__name__)


async def bypass(url: str) -> Optional[str]:
    """Bypass an MDisk URL to get direct link."""
    logger.info(f"[MDisk] Bypassing: {url[:80]}")

    # Extract the file ID from URL
    parsed = urlparse(url)
    path_parts = parsed.path.strip('/').split('/')
    file_id = path_parts[-1] if path_parts else ''

    if not file_id:
        return None

    domain = get_domain(url)

    try:
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            # Try MDisk API
            api_urls = [
                f"https://diskuploader.entertainvideo.com/v1/file/cdnurl?param={file_id}",
                f"https://{domain}/api/file/{file_id}",
                f"https://api.mdisk.me/api/v1/file/{file_id}",
            ]

            for api_url in api_urls:
                try:
                    resp = await client.get(api_url, headers={
                        'User-Agent': random.choice(USER_AGENTS),
                        'Accept': 'application/json',
                        'Referer': url,
                    })
                    if resp.status_code == 200:
                        data = resp.json()
                        # Different MDisk API response formats
                        result = (
                            data.get('download') or
                            data.get('source') or
                            data.get('direct_link') or
                            data.get('url') or
                            (data.get('data', {}) or {}).get('download_url') or
                            (data.get('data', {}) or {}).get('direct_download')
                        )
                        if result and is_valid_url(str(result)):
                            logger.info(f"[MDisk] API success: {result[:80]}")
                            return str(result)
                except Exception:
                    continue

            # Fallback: scrape the page
            resp = await client.get(url, headers={
                'User-Agent': random.choice(USER_AGENTS),
                'Accept': 'text/html',
            })
            if resp.status_code == 200:
                html = resp.text
                # Look for video/download source
                source_match = re.search(r'(?:source|src)\s*[:=]\s*["\']([^"\']+\.(?:mp4|mkv|avi|zip|rar|pdf)[^"\']*)["\']', html, re.IGNORECASE)
                if source_match:
                    return source_match.group(1)

                # Look for download button
                dl_match = re.search(r'href=["\']([^"\']+)["\'][^>]*(?:download|direct)', html, re.IGNORECASE)
                if dl_match:
                    found = dl_match.group(1)
                    if is_valid_url(found) and get_domain(found) != domain:
                        return found

    except Exception as e:
        logger.debug(f"[MDisk] Error: {e}")

    return None

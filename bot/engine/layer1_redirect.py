"""
LinkBypass Pro — Layer 1: HTTP Redirect Following
===================================================
The simplest and fastest bypass method. Follows HTTP 301/302/307/308
redirects through the entire chain until we reach a non-redirect response.
Works for simple URL shorteners like bit.ly, tinyurl, t.co, etc.
"""

import logging
import random
import re
from typing import Optional, Tuple
from urllib.parse import urlparse

import httpx

from bot.config import REDIRECT_TIMEOUT, MAX_REDIRECTS, USER_AGENTS, REFERER_POOL
from bot.engine.url_utils import (
    is_valid_url, get_domain, extract_meta_refresh,
    extract_js_redirects, is_destination_url
)

logger = logging.getLogger(__name__)

# Common ad/tracking domains to skip during redirect chain
SKIP_DOMAINS = {
    'googleads.g.doubleclick.net', 'pagead2.googlesyndication.com',
    'ad.doubleclick.net', 'ads.google.com', 'analytics.google.com',
    'facebook.com/tr', 'connect.facebook.net',
    'platform.twitter.com', 'syndication.twitter.com',
}


def _get_headers(referer: str = None) -> dict:
    """Generate browser-like request headers."""
    ua = random.choice(USER_AGENTS)
    headers = {
        'User-Agent': ua,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }
    if referer:
        headers['Referer'] = referer
        headers['Sec-Fetch-Site'] = 'cross-site'
    else:
        headers['Referer'] = random.choice(REFERER_POOL)
    return headers


async def attempt(url: str) -> Optional[str]:
    """
    Attempt to bypass a URL by following HTTP redirects.

    This layer handles:
    1. Standard HTTP 301/302/307/308 redirects
    2. Meta refresh redirects in HTML
    3. Simple JavaScript redirects (window.location)
    4. Link header redirects

    Returns the final destination URL, or None if no redirect found.
    """
    logger.info(f"[Layer1] Starting redirect follow for: {url[:80]}")

    original_domain = get_domain(url)
    visited = set()
    current_url = url
    hops = 0

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(REDIRECT_TIMEOUT),
            follow_redirects=False,  # We follow manually to inspect each hop
            verify=False,
            limits=httpx.Limits(max_connections=5),
        ) as client:

            while hops < MAX_REDIRECTS:
                if current_url in visited:
                    logger.warning(f"[Layer1] Redirect loop detected at hop {hops}")
                    break
                visited.add(current_url)

                try:
                    headers = _get_headers(referer=url if hops == 0 else current_url)
                    resp = await client.get(current_url, headers=headers)
                    hops += 1

                    # Check for HTTP redirect (3xx)
                    if resp.status_code in (301, 302, 303, 307, 308):
                        location = resp.headers.get('location', '')
                        if location:
                            # Handle relative URLs
                            if not location.startswith('http'):
                                parsed = urlparse(current_url)
                                if location.startswith('/'):
                                    location = f"{parsed.scheme}://{parsed.netloc}{location}"
                                else:
                                    location = f"{parsed.scheme}://{parsed.netloc}/{location}"

                            # Skip ad/tracking redirects
                            loc_domain = get_domain(location)
                            if loc_domain in SKIP_DOMAINS:
                                logger.debug(f"[Layer1] Skipping ad redirect: {loc_domain}")
                                continue

                            logger.debug(f"[Layer1] Hop {hops}: {resp.status_code} -> {location[:80]}")
                            current_url = location

                            # If we've left the shortener domain, likely reached destination
                            if get_domain(current_url) != original_domain and hops > 1:
                                if is_valid_url(current_url):
                                    logger.info(f"[Layer1] Destination found after {hops} hops: {current_url[:80]}")
                                    return current_url
                            continue

                    # If we got a 200, check if the domain changed (redirect happened via JS or meta)
                    if resp.status_code == 200:
                        response_url = str(resp.url)
                        if response_url != current_url:
                            if get_domain(response_url) != original_domain:
                                logger.info(f"[Layer1] URL changed during request: {response_url[:80]}")
                                return response_url

                        # Check response body for meta refresh or JS redirect
                        if resp.headers.get('content-type', '').startswith('text/html'):
                            body = resp.text[:50000]  # First 50KB

                            # Meta refresh
                            meta_url = extract_meta_refresh(body)
                            if meta_url and get_domain(meta_url) != original_domain:
                                logger.info(f"[Layer1] Meta refresh found: {meta_url[:80]}")
                                return meta_url

                            # JS redirects
                            js_urls = extract_js_redirects(body)
                            for js_url in js_urls:
                                if get_domain(js_url) != original_domain and is_valid_url(js_url):
                                    logger.info(f"[Layer1] JS redirect found: {js_url[:80]}")
                                    return js_url

                        # Check Link header
                        link_header = resp.headers.get('link', '')
                        if link_header:
                            link_match = re.search(r'<([^>]+)>;\s*rel=["\']?canonical', link_header)
                            if link_match:
                                canonical = link_match.group(1)
                                if is_valid_url(canonical) and get_domain(canonical) != original_domain:
                                    return canonical

                        # If URL hasn't changed and no redirect found in body, we're stuck
                        break

                    # Non-200, non-3xx status
                    logger.debug(f"[Layer1] Got status {resp.status_code} at hop {hops}")
                    break

                except httpx.TimeoutException:
                    logger.debug(f"[Layer1] Timeout at hop {hops}")
                    break
                except httpx.ConnectError as e:
                    logger.debug(f"[Layer1] Connection error: {e}")
                    break

    except Exception as e:
        logger.debug(f"[Layer1] Error: {type(e).__name__}: {e}")

    # If we followed redirects and ended up on a different domain
    if current_url != url and get_domain(current_url) != original_domain:
        if is_valid_url(current_url):
            return current_url

    return None

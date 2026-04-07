"""
LinkBypass Pro — Generic Bypass Patterns
==========================================
Handles unknown shorteners using generic techniques:
1. Form extraction and submission
2. JavaScript redirect detection
3. Meta refresh detection
4. Common URL patterns in HTML
5. Base64/encoding detection
"""

import re
import json
import logging
import random
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx

from bot.config import PATTERN_TIMEOUT, USER_AGENTS
from bot.engine.url_utils import (
    is_valid_url, get_domain, extract_csrf_token,
    extract_hidden_inputs, extract_form_action,
    extract_meta_refresh, extract_js_redirects,
    try_base64_decode, try_hex_decode
)

logger = logging.getLogger(__name__)


async def bypass(url: str) -> Optional[str]:
    """Generic bypass attempt for unknown shorteners."""
    logger.info(f"[Generic] Attempting generic bypass: {url[:80]}")
    domain = get_domain(url)

    try:
        async with httpx.AsyncClient(
            timeout=PATTERN_TIMEOUT,
            follow_redirects=False,
            verify=False,
        ) as client:
            headers = {
                'User-Agent': random.choice(USER_AGENTS),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.google.com/',
            }

            resp = await client.get(url, headers=headers)

            # Handle redirect chain
            hops = 0
            while resp.status_code in (301, 302, 303, 307, 308) and hops < 10:
                location = resp.headers.get('location', '')
                if not location:
                    break
                if not location.startswith('http'):
                    location = urljoin(str(resp.url or url), location)
                if get_domain(location) != domain and is_valid_url(location):
                    return location
                resp = await client.get(location, headers=headers)
                hops += 1

            if resp.status_code != 200:
                return None

            html = resp.text
            current_url = str(resp.url or url)

            # Method 1: Meta refresh
            meta = extract_meta_refresh(html)
            if meta and get_domain(meta) != domain:
                return meta

            # Method 2: JavaScript redirects
            js_urls = extract_js_redirects(html)
            for u in js_urls:
                if get_domain(u) != domain and is_valid_url(u):
                    return u

            # Method 3: Common destination link patterns
            dest_patterns = [
                r'<a[^>]*(?:id|class)=["\'][^"\']*(?:btn-primary|download|continue|proceed|go|skip|getlink|bypass|destination|unlock)[^"\']*["\'][^>]*href=["\']([^"\']+)["\']',
                r'href=["\']([^"\']+)["\'][^>]*(?:id|class)=["\'][^"\']*(?:btn-primary|download|continue|proceed|go|skip|getlink|bypass|destination|unlock)[^"\']*["\']',
                r'<a[^>]*href=["\']([^"\']*(?:mega|drive\.google|mediafire|dropbox|gofile|pixeldrain|terabox|hubcloud|gdtot|filepress)[^"\']*)["\']',
                r'<a[^>]*href=["\']([^"\']+)["\'][^>]*target=["\']_blank["\']',
            ]

            for pat in dest_patterns:
                m = re.search(pat, html, re.IGNORECASE)
                if m:
                    found = m.group(1)
                    if not found.startswith('http'):
                        found = urljoin(current_url, found)
                    if get_domain(found) != domain and is_valid_url(found):
                        return found

            # Method 4: Form submission
            form_action = extract_form_action(html)
            if form_action:
                inputs = extract_hidden_inputs(html)
                csrf = extract_csrf_token(html)
                if csrf:
                    inputs['_token'] = csrf

                if not form_action.startswith('http'):
                    form_action = urljoin(current_url, form_action)

                form_resp = await client.post(
                    form_action,
                    data=inputs,
                    headers={**headers, 'Referer': current_url}
                )

                if form_resp.status_code in (301, 302):
                    loc = form_resp.headers.get('location', '')
                    if loc and is_valid_url(loc) and get_domain(loc) != domain:
                        return loc

                if form_resp.status_code == 200:
                    for u in extract_js_redirects(form_resp.text[:20000]):
                        if get_domain(u) != domain and is_valid_url(u):
                            return u

            # Method 5: Base64 encoded URLs in page
            for m in re.finditer(r'["\']([A-Za-z0-9+/]{30,}={0,2})["\']', html):
                decoded = try_base64_decode(m.group(1))
                if decoded and get_domain(decoded) != domain:
                    return decoded

            # Method 6: URL in data attributes
            data_attrs = re.findall(r'data-(?:url|href|link|destination|redirect|target)\s*=\s*["\']([^"\']+)["\']', html, re.IGNORECASE)
            for attr_url in data_attrs:
                if not attr_url.startswith('http'):
                    attr_url = urljoin(current_url, attr_url)
                if is_valid_url(attr_url) and get_domain(attr_url) != domain:
                    return attr_url

    except Exception as e:
        logger.debug(f"[Generic] Error: {e}")

    return None

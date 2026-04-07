"""
LinkBypass Pro — Layer 4: Browser-Based Scraping
==================================================
Uses cloudscraper to handle JavaScript challenges, Cloudflare
protection, and other anti-bot measures. More sophisticated
than simple HTTP requests but lighter than a full headless browser.
"""

import re
import logging
import random
import time
from typing import Optional

from bot.config import BROWSER_TIMEOUT, USER_AGENTS
from bot.engine.url_utils import (
    is_valid_url, get_domain, extract_meta_refresh,
    extract_js_redirects, extract_form_action, extract_hidden_inputs,
    extract_csrf_token, try_base64_decode
)

logger = logging.getLogger(__name__)


async def attempt(url: str) -> Optional[str]:
    """
    Attempt bypass using cloudscraper (handles Cloudflare, JS challenges).

    This layer:
    1. Creates a cloudscraper session that handles JS challenges
    2. Fetches the page
    3. Follows any redirects (cloudscraper handles Cloudflare challenges)
    4. Extracts destination URLs from JS/HTML patterns
    5. Handles form-based redirects

    Returns destination URL or None.
    """
    logger.info(f"[Layer4] Starting cloudscraper bypass for: {url[:80]}")
    original_domain = get_domain(url)

    try:
        import cloudscraper
    except ImportError:
        logger.warning("[Layer4] cloudscraper not installed, skipping")
        return None

    try:
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False,
            },
            delay=3,
        )
        scraper.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': random.choice([
                'https://www.google.com/',
                'https://t.me/',
                'https://www.google.co.in/',
            ]),
        })

        # Step 1: Initial GET
        resp = scraper.get(url, allow_redirects=True, timeout=BROWSER_TIMEOUT)
        final_url = str(resp.url)
        status = resp.status_code

        logger.debug(f"[Layer4] Initial response: status={status}, final_url={final_url[:80]}")

        # Check if redirect happened
        if final_url != url and get_domain(final_url) != original_domain:
            if is_valid_url(final_url):
                logger.info(f"[Layer4] Cloudscraper redirect found: {final_url[:80]}")
                return final_url

        if status != 200:
            return None

        html = resp.text

        # Step 2: Check for various URL extraction patterns
        # Pattern: JavaScript variable assignments
        js_patterns = [
            r'var\s+url\s*=\s*["\']([^"\']+)["\']',
            r'var\s+link\s*=\s*["\']([^"\']+)["\']',
            r'var\s+redirect\s*=\s*["\']([^"\']+)["\']',
            r'var\s+destination\s*=\s*["\']([^"\']+)["\']',
            r'var\s+go_url\s*=\s*["\']([^"\']+)["\']',
            r'var\s+target\s*=\s*["\']([^"\']+)["\']',
            r'data-url\s*=\s*["\']([^"\']+)["\']',
            r'data-href\s*=\s*["\']([^"\']+)["\']',
            r'data-redirect\s*=\s*["\']([^"\']+)["\']',
        ]

        for pat in js_patterns:
            m = re.search(pat, html, re.IGNORECASE)
            if m:
                found = m.group(1)
                if found.startswith('http') and get_domain(found) != original_domain:
                    if is_valid_url(found):
                        logger.info(f"[Layer4] JS variable URL found: {found[:80]}")
                        return found

        # Pattern: Common destination link selectors
        link_patterns = [
            r'href=["\']([^"\']*(?:mega|drive\.google|mediafire|dropbox|gofile|pixeldrain|krakenfiles|hubcloud|gdtot|filepress|terabox)[^"\']*)["\']',
            r'href=["\']([^"\']+)["\'][^>]*(?:id|class)=["\'][^"\']*(?:download|bypass|destination|result|go|link|btn)[^"\']*["\']',
            r'window\.open\(["\']([^"\']+)["\']',
            r'onclick=["\'][^"\']*window\.location\s*=\s*["\']?([^"\';\s]+)',
        ]

        for pat in link_patterns:
            m = re.search(pat, html, re.IGNORECASE)
            if m:
                found = m.group(1)
                if found.startswith('http') and get_domain(found) != original_domain:
                    if is_valid_url(found):
                        logger.info(f"[Layer4] Link pattern URL found: {found[:80]}")
                        return found

        # Pattern: Base64 encoded URLs
        b64_patterns = [
            r'atob\(["\']([A-Za-z0-9+/=]+)["\']',
            r'base64[,:\s]*["\']?([A-Za-z0-9+/=]{20,})',
            r'decode\(["\']([A-Za-z0-9+/=]{20,})["\']',
        ]

        for pat in b64_patterns:
            for m in re.finditer(pat, html):
                decoded = try_base64_decode(m.group(1))
                if decoded and get_domain(decoded) != original_domain:
                    logger.info(f"[Layer4] Base64 decoded URL: {decoded[:80]}")
                    return decoded

        # Pattern: Meta refresh
        meta_url = extract_meta_refresh(html)
        if meta_url and get_domain(meta_url) != original_domain:
            logger.info(f"[Layer4] Meta refresh URL: {meta_url[:80]}")
            return meta_url

        # Step 3: Try form submission if form exists
        form_action = extract_form_action(html)
        if form_action:
            hidden_inputs = extract_hidden_inputs(html)
            csrf = extract_csrf_token(html)
            if csrf:
                hidden_inputs['_token'] = csrf

            # Construct absolute URL for form action
            if not form_action.startswith('http'):
                from urllib.parse import urljoin
                form_action = urljoin(url, form_action)

            try:
                form_resp = scraper.post(
                    form_action,
                    data=hidden_inputs,
                    allow_redirects=True,
                    timeout=BROWSER_TIMEOUT
                )
                form_final = str(form_resp.url)
                if form_final != url and get_domain(form_final) != original_domain:
                    if is_valid_url(form_final):
                        logger.info(f"[Layer4] Form submission redirect: {form_final[:80]}")
                        return form_final

                # Check form response for URLs
                if form_resp.status_code == 200:
                    form_html = form_resp.text
                    js_urls = extract_js_redirects(form_html)
                    for js_url in js_urls:
                        if get_domain(js_url) != original_domain and is_valid_url(js_url):
                            logger.info(f"[Layer4] Form response JS URL: {js_url[:80]}")
                            return js_url
            except Exception as e:
                logger.debug(f"[Layer4] Form submission error: {e}")

        return None

    except Exception as e:
        logger.debug(f"[Layer4] Error: {type(e).__name__}: {e}")
        return None

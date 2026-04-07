"""
LinkBypass Pro — Layer 5: Multi-Strategy Advanced Bypass
=========================================================
Last resort layer combining multiple advanced techniques:
- Session-based multi-step navigation
- AJAX endpoint discovery
- Token extraction and form submission
- Base64/encoding tricks
- API endpoint brute-forcing
"""

import re
import logging
import random
import time
import json
import hashlib
import base64
from typing import Optional
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, quote

import httpx

from bot.config import HEADLESS_TIMEOUT, USER_AGENTS
from bot.engine.url_utils import (
    is_valid_url, get_domain, extract_meta_refresh,
    extract_js_redirects, extract_form_action, extract_hidden_inputs,
    extract_csrf_token, try_base64_decode, extract_countdown,
    is_destination_url
)

logger = logging.getLogger(__name__)


class AdvancedBypasser:
    """Multi-strategy bypass engine for the most stubborn shorteners."""

    def __init__(self):
        self.session: Optional[httpx.AsyncClient] = None
        self.cookies = {}
        self.original_url = ""
        self.original_domain = ""
        self.visited = set()

    async def __aenter__(self):
        self.session = httpx.AsyncClient(
            timeout=httpx.Timeout(HEADLESS_TIMEOUT),
            follow_redirects=True,
            verify=False,
            limits=httpx.Limits(max_connections=10),
        )
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.aclose()

    def _headers(self, referer: str = None, ajax: bool = False) -> dict:
        ua = random.choice(USER_AGENTS)
        h = {
            'User-Agent': ua,
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        if ajax:
            h['X-Requested-With'] = 'XMLHttpRequest'
            h['Accept'] = 'application/json, text/javascript, */*; q=0.01'
        else:
            h['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        if referer:
            h['Referer'] = referer
        return h

    async def _try_adlinkfly_api(self, url: str) -> Optional[str]:
        """Try common AdLinkFly API endpoints."""
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        slug = parsed.path.strip('/')

        # Common AdLinkFly API patterns
        api_endpoints = [
            f"{base}/api?api=&url={quote(url)}&type=1",
            f"{base}/links/{slug}",
            f"{base}/ajax/check_redirect",
            f"{base}/redirect/{slug}",
        ]

        for endpoint in api_endpoints:
            try:
                resp = await self.session.get(
                    endpoint,
                    headers=self._headers(referer=url, ajax=True),
                )
                if resp.status_code == 200:
                    text = resp.text
                    # Try JSON response
                    try:
                        data = json.loads(text)
                        for key in ['url', 'link', 'destination', 'dest', 'redirect_url', 'shortenedUrl']:
                            if key in data and is_valid_url(str(data[key])):
                                return str(data[key])
                    except:
                        pass
                    # Try finding URL in response
                    urls = re.findall(r'https?://[^\s"\'>]+', text)
                    for u in urls:
                        if get_domain(u) != self.original_domain and is_destination_url(u, self.original_domain):
                            return u
            except:
                continue
        return None

    async def _try_form_submission(self, html: str, page_url: str) -> Optional[str]:
        """Extract and submit forms that may contain bypass tokens."""
        form_action = extract_form_action(html)
        if not form_action:
            return None

        action_url = urljoin(page_url, form_action)
        hidden = extract_hidden_inputs(html)
        csrf = extract_csrf_token(html)
        if csrf:
            hidden['_token'] = csrf

        try:
            resp = await self.session.post(
                action_url,
                data=hidden,
                headers=self._headers(referer=page_url),
            )
            dest = str(resp.url)
            if get_domain(dest) != self.original_domain and is_destination_url(dest, self.original_domain):
                return dest
            
            # Check response for redirect URLs
            text = resp.text
            meta = extract_meta_refresh(text)
            if meta and is_valid_url(meta):
                return meta
            js_redir = extract_js_redirects(text)
            if js_redir and is_valid_url(js_redir):
                return js_redir
        except:
            pass
        return None

    async def _try_source_extraction(self, html: str) -> Optional[str]:
        """Extract destination from page source patterns."""
        patterns = [
            r'var\s+url\s*=\s*["\'](https?://[^"\'>]+)',
            r'var\s+(?:dest|link|redirect|go_url|final_url)\s*=\s*["\'](https?://[^"\'>]+)',
            r'window\.location(?:\.href)?\s*=\s*["\'](https?://[^"\'>]+)',
            r'window\.open\(["\'](https?://[^"\'>]+)',
            r'<meta[^>]+url=(https?://[^"\'>]+)',
            r'href=["\'](https?://[^"\'>]+)["\'"][^>]*>\s*(?:Get|Go|Click|Continue|Download|Direct)',
            r'data-url=["\'](https?://[^"\'>]+)',
            r'action=["\'](https?://(?!(?:' + re.escape(self.original_domain) + r'))[^"\'>]+)',
            r'"redirect"\s*:\s*"(https?://[^"]+)"',
            r'"url"\s*:\s*"(https?://[^"]+)"',
            r'"destination"\s*:\s*"(https?://[^"]+)"',
            r'base64["\'\s]*[:,]\s*["\']((?:[A-Za-z0-9+/]{4}){5,}={0,2})',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, html, re.I)
            for match in matches:
                # Handle base64-encoded URLs
                if re.match(r'^[A-Za-z0-9+/]{20,}={0,2}$', match):
                    decoded = try_base64_decode(match)
                    if decoded and is_valid_url(decoded):
                        match = decoded

                if is_valid_url(match) and get_domain(match) != self.original_domain:
                    if is_destination_url(match, self.original_domain):
                        return match
        return None

    async def _try_multi_step(self, url: str) -> Optional[str]:
        """Handle multi-step bypass (initial page -> wait -> form -> destination)."""
        try:
            resp = await self.session.get(url, headers=self._headers())
            if resp.status_code != 200:
                return None

            html = resp.text
            page_url = str(resp.url)

            # Check direct redirect
            if get_domain(page_url) != self.original_domain:
                if is_destination_url(page_url, self.original_domain):
                    return page_url

            # Step 1: Extract from source
            result = await self._try_source_extraction(html)
            if result:
                return result

            # Step 2: Try form submission
            result = await self._try_form_submission(html, page_url)
            if result:
                return result

            # Step 3: Try API endpoints
            result = await self._try_adlinkfly_api(url)
            if result:
                return result

            return None
        except:
            return None

    async def bypass(self, url: str) -> Optional[str]:
        """Main bypass entry point. Tries all strategies."""
        self.original_url = url
        self.original_domain = get_domain(url)

        strategies = [
            self._try_multi_step,
            self._try_adlinkfly_api,
        ]

        for strategy in strategies:
            try:
                result = await strategy(url)
                if result and is_valid_url(result):
                    logger.info(f"[Layer5] Success via {strategy.__name__}: {result[:80]}")
                    return result
            except Exception as e:
                logger.debug(f"[Layer5] {strategy.__name__} failed: {e}")
                continue

        return None


async def attempt(url: str) -> Optional[str]:
    """Layer 5 entry point."""
    logger.info(f"[Layer5] Advanced bypass for: {url[:80]}")
    try:
        async with AdvancedBypasser() as bypasser:
            return await bypasser.bypass(url)
    except Exception as e:
        logger.error(f"[Layer5] Error: {e}")
        return None

"""
LinkBypass Pro — Layer 5: Advanced Headless Approach
=====================================================
Uses a sophisticated multi-technique approach for the most
stubborn shorteners that resist simpler methods. Combines
multiple request strategies, cookie manipulation, and
response parsing.
"""

import re
import logging
import random
import time
import json
import hashlib
from typing import Optional
from urllib.parse import urljoin, urlparse, parse_qs

import httpx

from bot.config import HEADLESS_TIMEOUT, USER_AGENTS
from bot.engine.url_utils import (
    is_valid_url, get_domain, extract_meta_refresh,
    extract_js_redirects, extract_form_action, extract_hidden_inputs,
    extract_csrf_token, try_base64_decode, extract_countdown
)

logger = logging.getLogger(__name__)


class AdvancedBypasser:
    """
    Advanced bypass engine that simulates complex browser behavior
    including cookie handling, form submissions, AJAX requests,
    and multi-step navigation.
    """

    def __init__(self):
        self.session: Optional[httpx.AsyncClient] = None
        self.cookies = {}
        self.original_url = ""
        self.original_domain = ""

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
        """Generate realistic browser headers."""
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
            h['Accept'] = 'application/json, text/javascript, */*; q=0.01'
            h['X-Requested-With'] = 'XMLHttpRequest'
        else:
            h['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'

        if referer:
            h['Referer'] = referer

        return h

    async def _get(self, url: str, referer: str = None, ajax: bool = False) -> Optional[httpx.Response]:
        """Make a GET request with error handling."""
        try:
            resp = await self.session.get(url, headers=self._headers(referer, ajax))
            return resp
        except Exception as e:
            logger.debug(f"[Layer5] GET error for {url[:60]}: {e}")
            return None

    async def _post(self, url: str, data: dict = None, json_data: dict = None,
                    referer: str = None, ajax: bool = False) -> Optional[httpx.Response]:
        """Make a POST request with error handling."""
        try:
            headers = self._headers(referer, ajax)
            if json_data:
                headers['Content-Type'] = 'application/json'
                resp = await self.session.post(url, json=json_data, headers=headers)
            else:
                headers['Content-Type'] = 'application/x-www-form-urlencoded'
                resp = await self.session.post(url, data=data or {}, headers=headers)
            return resp
        except Exception as e:
            logger.debug(f"[Layer5] POST error for {url[:60]}: {e}")
            return None

    async def bypass(self, url: str) -> Optional[str]:
        """Main bypass method — tries multiple strategies."""
        self.original_url = url
        self.original_domain = get_domain(url)

        # Strategy 1: Multi-step redirect following with cookie persistence
        result = await self._strategy_cookie_redirect(url)
        if result:
            return result

        # Strategy 2: Form submission with token extraction
        result = await self._strategy_form_submit(url)
        if result:
            return result

        # Strategy 3: AJAX endpoint discovery
        result = await self._strategy_ajax_discovery(url)
        if result:
            return result

        # Strategy 4: JavaScript eval simulation
        result = await self._strategy_js_eval(url)
        if result:
            return result

        return None

    async def _strategy_cookie_redirect(self, url: str) -> Optional[str]:
        """Follow redirects with persistent cookies across multiple requests."""
        logger.debug("[Layer5] Strategy: Cookie redirect")

        resp = await self._get(url, referer='https://www.google.com/')
        if not resp:
            return None

        # Check if we got redirected
        final = str(resp.url)
        if final != url and get_domain(final) != self.original_domain:
            if is_valid_url(final):
                return final

        if resp.status_code != 200:
            return None

        html = resp.text

        # Check for JS-based cookie + redirect pattern
        # Many shorteners set cookies via JS then redirect
        cookie_patterns = [
            r'document\.cookie\s*=\s*["\']([^"\']+)["\']',
        ]
        for pat in cookie_patterns:
            matches = re.findall(pat, html)
            for cookie_str in matches:
                # Parse cookie
                parts = cookie_str.split(';')
                if parts:
                    kv = parts[0].split('=', 1)
                    if len(kv) == 2:
                        self.session.cookies.set(kv[0].strip(), kv[1].strip())

        # After setting cookies, try fetching again
        if self.session.cookies:
            resp2 = await self._get(url, referer=url)
            if resp2:
                final2 = str(resp2.url)
                if final2 != url and get_domain(final2) != self.original_domain:
                    if is_valid_url(final2):
                        return final2

                # Check response for redirect URLs
                for u in extract_js_redirects(resp2.text[:30000]):
                    if get_domain(u) != self.original_domain and is_valid_url(u):
                        return u

        return None

    async def _strategy_form_submit(self, url: str) -> Optional[str]:
        """Handle multi-step form-based redirects."""
        logger.debug("[Layer5] Strategy: Form submit")

        resp = await self._get(url)
        if not resp or resp.status_code != 200:
            return None

        html = resp.text

        # Find all forms in the page
        form_pattern = r'<form[^>]*>(.*?)</form>'
        forms = re.findall(form_pattern, html, re.DOTALL | re.IGNORECASE)

        for form_html in forms:
            # Get form action
            action_match = re.search(
                r'<form[^>]*action=["\']([^"\']*)["\']',
                html, re.IGNORECASE
            )
            action = action_match.group(1) if action_match else url

            if not action.startswith('http'):
                action = urljoin(url, action)

            # Get method
            method_match = re.search(
                r'<form[^>]*method=["\']([^"\']*)["\']',
                html, re.IGNORECASE
            )
            method = (method_match.group(1) if method_match else 'POST').upper()

            # Collect all inputs
            inputs = extract_hidden_inputs(html)
            csrf = extract_csrf_token(html)
            if csrf:
                inputs['_token'] = csrf

            if not inputs:
                continue

            # Submit form
            if method == 'POST':
                form_resp = await self._post(action, data=inputs, referer=url)
            else:
                form_resp = await self._get(f"{action}?{'&'.join(f'{k}={v}' for k,v in inputs.items())}", referer=url)

            if form_resp:
                form_final = str(form_resp.url)
                if get_domain(form_final) != self.original_domain and is_valid_url(form_final):
                    return form_final

                # Check response body
                if form_resp.status_code == 200:
                    for u in extract_js_redirects(form_resp.text[:30000]):
                        if get_domain(u) != self.original_domain and is_valid_url(u):
                            return u

                    meta = extract_meta_refresh(form_resp.text[:10000])
                    if meta and get_domain(meta) != self.original_domain:
                        return meta

        return None

    async def _strategy_ajax_discovery(self, url: str) -> Optional[str]:
        """Discover and call AJAX endpoints that return the destination URL."""
        logger.debug("[Layer5] Strategy: AJAX discovery")

        resp = await self._get(url)
        if not resp or resp.status_code != 200:
            return None

        html = resp.text
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"

        # Look for AJAX endpoints in JavaScript
        ajax_patterns = [
            # jQuery AJAX
            r'\$\.(?:ajax|get|post)\s*\(\s*["\']([^"\']+)["\']',
            r'url\s*:\s*["\']([^"\']+/(?:api|bypass|go|redirect|get|link|unlock)[^"\']*)["\']',

            # Fetch API
            r'fetch\s*\(\s*["\']([^"\']+)["\']',

            # XMLHttpRequest
            r'\.open\s*\(\s*["\'](?:GET|POST)["\'],\s*["\']([^"\']+)["\']',

            # Common API endpoint patterns
            r'(?:api_url|apiUrl|endpoint|ajax_url)\s*[:=]\s*["\']([^"\']+)["\']',
        ]

        endpoints = []
        for pat in ajax_patterns:
            for m in re.finditer(pat, html, re.IGNORECASE):
                ep = m.group(1)
                if not ep.startswith('http'):
                    ep = urljoin(url, ep)
                if get_domain(ep) == self.original_domain:
                    endpoints.append(ep)

        # Try each discovered endpoint
        for ep in endpoints[:5]:  # Limit to 5 attempts
            # Try GET
            ajax_resp = await self._get(ep, referer=url, ajax=True)
            if ajax_resp and ajax_resp.status_code == 200:
                result = self._extract_url_from_response(ajax_resp.text)
                if result:
                    return result

            # Try POST with common payloads
            path_id = re.search(r'/([a-zA-Z0-9]+)/?$', url)
            if path_id:
                for payload in [
                    {'id': path_id.group(1)},
                    {'link_id': path_id.group(1)},
                    {'code': path_id.group(1)},
                    {'alias': path_id.group(1)},
                ]:
                    post_resp = await self._post(ep, json_data=payload, referer=url, ajax=True)
                    if post_resp and post_resp.status_code == 200:
                        result = self._extract_url_from_response(post_resp.text)
                        if result:
                            return result

        return None

    async def _strategy_js_eval(self, url: str) -> Optional[str]:
        """Simulate JavaScript evaluation to extract URLs."""
        logger.debug("[Layer5] Strategy: JS eval simulation")

        resp = await self._get(url)
        if not resp or resp.status_code != 200:
            return None

        html = resp.text

        # Pattern: Concatenated strings
        # var url = "htt" + "ps:" + "//exa" + "mple.com/path"
        concat_pattern = r'(?:var|let|const)\s+\w+\s*=\s*(["\'][^"\']*["\'](?:\s*\+\s*["\'][^"\']*["\'])+)'
        for m in re.finditer(concat_pattern, html):
            parts = re.findall(r'["\']([^"\']*)["\']', m.group(1))
            if parts:
                assembled = ''.join(parts)
                if is_valid_url(assembled) and get_domain(assembled) != self.original_domain:
                    return assembled

        # Pattern: String reversal
        # var url = "moc.elpmaxe//:sptth".split("").reverse().join("")
        reverse_pattern = r'["\']([^"\']+)["\']\.split\(["\']["\']?\)\.reverse\(\)\.join\('
        for m in re.finditer(reverse_pattern, html):
            reversed_str = m.group(1)[::-1]
            if is_valid_url(reversed_str) and get_domain(reversed_str) != self.original_domain:
                return reversed_str

        # Pattern: Char code arrays
        # String.fromCharCode(104,116,116,112,115,...)
        charcode_pattern = r'String\.fromCharCode\s*\(([\d,\s]+)\)'
        for m in re.finditer(charcode_pattern, html):
            try:
                codes = [int(c.strip()) for c in m.group(1).split(',')]
                decoded = ''.join(chr(c) for c in codes)
                if is_valid_url(decoded) and get_domain(decoded) != self.original_domain:
                    return decoded
            except (ValueError, OverflowError):
                pass

        # Pattern: Hex-encoded strings
        hex_pattern = r'\\x([0-9a-fA-F]{2})'
        hex_strings = re.findall(r'["\']((\\x[0-9a-fA-F]{2}){10,})["\']', html)
        for hex_str, _ in hex_strings:
            try:
                decoded = bytes.fromhex(
                    ''.join(re.findall(r'\\x([0-9a-fA-F]{2})', hex_str))
                ).decode('utf-8', errors='ignore')
                if is_valid_url(decoded) and get_domain(decoded) != self.original_domain:
                    return decoded
            except Exception:
                pass

        # Pattern: ROT13/Caesar cipher
        import codecs
        for m in re.finditer(r'["\']([A-Za-z0-9+/]{20,})["\']', html):
            candidate = m.group(1)
            # Try ROT13
            try:
                rot13 = codecs.decode(candidate, 'rot_13')
                if is_valid_url(rot13):
                    return rot13
            except Exception:
                pass

        return None

    def _extract_url_from_response(self, text: str) -> Optional[str]:
        """Extract a destination URL from an API/AJAX response."""
        # Try JSON
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                for key in ['url', 'link', 'destination', 'redirect', 'result',
                            'bypassed', 'target', 'goto', 'dest', 'go',
                            'destination_url', 'final_url', 'bypass_url']:
                    if key in data:
                        val = str(data[key])
                        if is_valid_url(val) and get_domain(val) != self.original_domain:
                            return val
                # Check nested data
                for key in ['data', 'response', 'body']:
                    if key in data and isinstance(data[key], dict):
                        for subkey in ['url', 'link', 'destination']:
                            if subkey in data[key]:
                                val = str(data[key][subkey])
                                if is_valid_url(val) and get_domain(val) != self.original_domain:
                                    return val
        except (json.JSONDecodeError, TypeError):
            pass

        # Try plain text URL
        text = text.strip()
        if is_valid_url(text) and get_domain(text) != self.original_domain:
            return text

        # Find URLs in response
        urls = re.findall(r'https?://[^\s"\'<>]+', text)
        for u in urls:
            if is_valid_url(u) and get_domain(u) != self.original_domain:
                return u

        return None


async def attempt(url: str) -> Optional[str]:
    """Attempt bypass using advanced headless techniques."""
    logger.info(f"[Layer5] Starting advanced bypass for: {url[:80]}")

    try:
        async with AdvancedBypasser() as bypasser:
            result = await bypasser.bypass(url)
            if result:
                logger.info(f"[Layer5] Advanced bypass success: {result[:80]}")
                return result
    except Exception as e:
        logger.debug(f"[Layer5] Error: {type(e).__name__}: {e}")

    return None

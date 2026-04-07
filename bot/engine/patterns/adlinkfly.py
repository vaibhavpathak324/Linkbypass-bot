"""
LinkBypass Pro — AdLinkFly CMS Pattern Bypass
===============================================
AdLinkFly is the most popular URL shortener CMS used by hundreds
of Indian and international shortener sites. This module handles
the bypass for all AdLinkFly-based sites.

How AdLinkFly works:
1. User visits short URL (e.g., shrinkme.io/XXXX)
2. Page loads with a timer countdown (usually 5-15 seconds)
3. After countdown, a "Go to link" button appears
4. Clicking the button POSTs to the same URL with form token
5. Server responds with the actual destination URL

Bypass approach:
1. GET the short URL
2. Extract CSRF token (_token) and form data
3. POST to the same URL (or /links/go) with the token
4. Extract destination from redirect or response body
"""

import re
import json
import logging
import random
import time
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx

from bot.config import PATTERN_TIMEOUT, USER_AGENTS, REFERER_POOL
from bot.engine.url_utils import (
    is_valid_url, get_domain, extract_csrf_token,
    extract_hidden_inputs, extract_form_action,
    extract_meta_refresh, extract_js_redirects,
    try_base64_decode
)

logger = logging.getLogger(__name__)


def _headers(url: str, referer: str = None, ajax: bool = False) -> dict:
    """Generate browser-like headers for AdLinkFly sites."""
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    h = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept-Language': 'en-US,en;q=0.9,hi;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Origin': origin,
    }

    if ajax:
        h['Accept'] = 'application/json, text/javascript, */*; q=0.01'
        h['X-Requested-With'] = 'XMLHttpRequest'
        h['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
    else:
        h['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        h['Upgrade-Insecure-Requests'] = '1'

    h['Referer'] = referer or url

    return h


async def bypass(url: str) -> Optional[str]:
    """
    Bypass an AdLinkFly-based shortener URL.
    Tries multiple strategies in order of reliability.
    """
    logger.info(f"[AdLinkFly] Bypassing: {url[:80]}")
    domain = get_domain(url)
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(PATTERN_TIMEOUT),
            follow_redirects=False,
            verify=False,
        ) as client:

            # Step 1: GET the short URL
            resp = await client.get(url, headers=_headers(url, random.choice(REFERER_POOL)))

            # Handle redirects manually
            redirect_count = 0
            while resp.status_code in (301, 302, 303, 307, 308) and redirect_count < 5:
                location = resp.headers.get('location', '')
                if not location:
                    break
                if not location.startswith('http'):
                    location = urljoin(str(resp.url), location)
                # Check if redirected to destination
                if get_domain(location) != domain:
                    if is_valid_url(location):
                        logger.info(f"[AdLinkFly] Direct redirect: {location[:80]}")
                        return location
                resp = await client.get(location, headers=_headers(location, url))
                redirect_count += 1

            if resp.status_code != 200:
                logger.debug(f"[AdLinkFly] Got status {resp.status_code}")
                return None

            html = resp.text
            current_url = str(resp.url)

            # Strategy 1: Try /links/go endpoint (most common)
            result = await _try_links_go(client, url, current_url, html, base_url, domain)
            if result:
                return result

            # Strategy 2: Try direct form POST
            result = await _try_form_post(client, url, current_url, html, base_url, domain)
            if result:
                return result

            # Strategy 3: Try AJAX link endpoint
            result = await _try_ajax_endpoint(client, url, current_url, html, base_url, domain)
            if result:
                return result

            # Strategy 4: Extract from JavaScript directly
            result = _extract_from_js(html, domain)
            if result:
                return result

            # Strategy 5: Try common AdLinkFly API patterns
            result = await _try_api_patterns(client, url, current_url, html, base_url, domain)
            if result:
                return result

            return None

    except Exception as e:
        logger.debug(f"[AdLinkFly] Error: {type(e).__name__}: {e}")
        return None


async def _try_links_go(client, original_url, current_url, html, base_url, domain) -> Optional[str]:
    """Try the /links/go endpoint used by most AdLinkFly sites."""
    # Extract the link alias/ID from URL
    parsed = urlparse(current_url)
    path_parts = parsed.path.strip('/').split('/')
    alias = path_parts[-1] if path_parts else ''

    if not alias:
        return None

    # Extract CSRF token
    csrf = extract_csrf_token(html)
    if not csrf:
        # Look for alternative token patterns
        token_patterns = [
            r'token\s*[:=]\s*["\']([^"\']+)["\']',
            r'csrfToken\s*[:=]\s*["\']([^"\']+)["\']',
            r'_csrf_token\s*[:=]\s*["\']([^"\']+)["\']',
        ]
        for pat in token_patterns:
            m = re.search(pat, html)
            if m:
                csrf = m.group(1)
                break

    # Common go endpoints
    go_urls = [
        f"{base_url}/links/go",
        f"{base_url}/link/go",
        f"{base_url}/go/{alias}",
        f"{base_url}/links/{alias}/go",
        f"{base_url}/api/links/go",
    ]

    # Common form data patterns
    form_payloads = []

    if csrf:
        form_payloads.extend([
            {'_token': csrf, 'alias': alias},
            {'_token': csrf, 'id': alias},
            {'_token': csrf, 'link': alias},
            {'token': csrf, 'alias': alias},
        ])
    else:
        form_payloads.extend([
            {'alias': alias},
            {'id': alias},
        ])

    # Also extract any hidden inputs from the page
    hidden = extract_hidden_inputs(html)
    if hidden:
        form_payloads.insert(0, hidden)

    for go_url in go_urls:
        for payload in form_payloads:
            try:
                resp = await client.post(
                    go_url,
                    data=payload,
                    headers=_headers(go_url, current_url, ajax=True),
                )

                result = _parse_go_response(resp, domain)
                if result:
                    logger.info(f"[AdLinkFly] /links/go success: {result[:80]}")
                    return result

            except Exception as e:
                logger.debug(f"[AdLinkFly] go endpoint error: {e}")
                continue

    return None


async def _try_form_post(client, original_url, current_url, html, base_url, domain) -> Optional[str]:
    """Try submitting the page form directly."""
    form_action = extract_form_action(html)
    if not form_action:
        # Some AdLinkFly sites POST to the same URL
        form_action = current_url

    if not form_action.startswith('http'):
        form_action = urljoin(current_url, form_action)

    # Collect form data
    inputs = extract_hidden_inputs(html)
    csrf = extract_csrf_token(html)
    if csrf:
        inputs['_token'] = csrf

    if not inputs:
        return None

    try:
        resp = await client.post(
            form_action,
            data=inputs,
            headers=_headers(form_action, current_url),
        )

        result = _parse_go_response(resp, domain)
        if result:
            logger.info(f"[AdLinkFly] Form POST success: {result[:80]}")
            return result

    except Exception as e:
        logger.debug(f"[AdLinkFly] Form POST error: {e}")

    return None


async def _try_ajax_endpoint(client, original_url, current_url, html, base_url, domain) -> Optional[str]:
    """Try AJAX endpoints found in the page JavaScript."""
    # Find AJAX URLs in scripts
    ajax_patterns = [
        r'\$\.(?:ajax|post|get)\s*\(\s*["\']([^"\']+)["\']',
        r'fetch\s*\(\s*["\']([^"\']+)["\']',
        r'xhr\.open\s*\(\s*["\'](?:GET|POST)["\'],\s*["\']([^"\']+)["\']',
        r'url\s*:\s*["\']([^"\']+(?:go|links|bypass|redirect|get-link)[^"\']*)["\']',
    ]

    endpoints = []
    for pat in ajax_patterns:
        for m in re.finditer(pat, html, re.IGNORECASE):
            ep = m.group(1)
            if not ep.startswith('http'):
                ep = urljoin(base_url, ep)
            endpoints.append(ep)

    csrf = extract_csrf_token(html)
    parsed = urlparse(current_url)
    alias = parsed.path.strip('/').split('/')[-1]

    for ep in endpoints[:5]:
        for method in ['POST', 'GET']:
            try:
                data = {'alias': alias}
                if csrf:
                    data['_token'] = csrf

                if method == 'POST':
                    resp = await client.post(
                        ep, data=data,
                        headers=_headers(ep, current_url, ajax=True)
                    )
                else:
                    resp = await client.get(
                        ep, params=data,
                        headers=_headers(ep, current_url, ajax=True)
                    )

                result = _parse_go_response(resp, domain)
                if result:
                    logger.info(f"[AdLinkFly] AJAX success from {ep}: {result[:80]}")
                    return result
            except Exception:
                continue

    return None


async def _try_api_patterns(client, original_url, current_url, html, base_url, domain) -> Optional[str]:
    """Try common AdLinkFly API endpoint patterns."""
    parsed = urlparse(current_url)
    alias = parsed.path.strip('/').split('/')[-1]

    # Some sites use REST-like APIs
    api_endpoints = [
        f"{base_url}/api/v1/links/{alias}",
        f"{base_url}/api/links/{alias}",
        f"{base_url}/api/link/{alias}",
        f"{base_url}/api/{alias}",
        f"{base_url}/get/{alias}",
        f"{base_url}/out/{alias}",
    ]

    for ep in api_endpoints:
        try:
            resp = await client.get(ep, headers=_headers(ep, current_url, ajax=True))
            if resp.status_code == 200:
                result = _parse_go_response(resp, domain)
                if result:
                    logger.info(f"[AdLinkFly] API pattern success: {result[:80]}")
                    return result
        except Exception:
            continue

    return None


def _extract_from_js(html: str, domain: str) -> Optional[str]:
    """Extract destination URL from JavaScript in the page."""
    # Pattern: URL stored in JS variable
    js_url_patterns = [
        r'var\s+(?:url|dest|destination|link|redirect|go_url|final_url)\s*=\s*["\']([^"\']+)["\']',
        r'(?:url|dest|destination|link|redirect)\s*:\s*["\']([^"\']+)["\']',
        r'window\.location\s*(?:\.href)?\s*=\s*["\']([^"\']+)["\']',
        r'location\.replace\(["\']([^"\']+)["\']',
        r'data-(?:url|href|link|destination)\s*=\s*["\']([^"\']+)["\']',
    ]

    for pat in js_url_patterns:
        for m in re.finditer(pat, html, re.IGNORECASE):
            found = m.group(1)
            if found.startswith('http') and get_domain(found) != domain:
                if is_valid_url(found):
                    return found

    # Pattern: Base64 encoded URL
    b64_patterns = [
        r'atob\(["\']([A-Za-z0-9+/=]+)["\']',
        r'window\.atob\(["\']([A-Za-z0-9+/=]+)["\']',
        r'decodeURIComponent\(atob\(["\']([A-Za-z0-9+/=]+)["\']',
    ]
    for pat in b64_patterns:
        for m in re.finditer(pat, html):
            decoded = try_base64_decode(m.group(1))
            if decoded and get_domain(decoded) != domain:
                return decoded

    # Pattern: Obfuscated in JSON config
    json_patterns = [
        r'var\s+config\s*=\s*(\{[^}]+\})',
        r'var\s+data\s*=\s*(\{[^}]+\})',
        r'window\.__data__\s*=\s*(\{.+?\});',
    ]
    for pat in json_patterns:
        m = re.search(pat, html, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(1))
                for key in ['url', 'link', 'destination', 'redirect']:
                    if key in data and is_valid_url(str(data[key])):
                        if get_domain(str(data[key])) != domain:
                            return str(data[key])
            except (json.JSONDecodeError, TypeError):
                pass

    return None


def _parse_go_response(resp: httpx.Response, domain: str) -> Optional[str]:
    """Parse the response from a /go or form POST request."""
    # Check redirect
    if resp.status_code in (301, 302, 303, 307, 308):
        location = resp.headers.get('location', '')
        if location and is_valid_url(location) and get_domain(location) != domain:
            return location

    if resp.status_code != 200:
        return None

    text = resp.text.strip()

    # Try JSON response
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            for key in ['url', 'link', 'destination', 'redirect', 'data',
                        'destination_url', 'go_url', 'target', 'bypass',
                        'result', 'final_url']:
                if key in data:
                    val = data[key]
                    if isinstance(val, str) and is_valid_url(val) and get_domain(val) != domain:
                        return val
                    if isinstance(val, dict):
                        for subkey in ['url', 'link', 'destination']:
                            if subkey in val and is_valid_url(str(val[subkey])):
                                return str(val[subkey])
            # Check success/status pattern
            if data.get('status') in ('success', True, 1, 'ok'):
                for key in data:
                    val = str(data[key])
                    if is_valid_url(val) and get_domain(val) != domain:
                        return val
    except (json.JSONDecodeError, TypeError):
        pass

    # Try plain URL
    if is_valid_url(text) and get_domain(text) != domain:
        return text

    # Find URLs in HTML response
    urls = re.findall(r'https?://[^\s"\'<>]+', text[:5000])
    for u in urls:
        u = u.rstrip('.,;:)')
        if is_valid_url(u) and get_domain(u) != domain:
            return u

    # Check for meta refresh in response
    meta = extract_meta_refresh(text[:5000])
    if meta and get_domain(meta) != domain:
        return meta

    return None

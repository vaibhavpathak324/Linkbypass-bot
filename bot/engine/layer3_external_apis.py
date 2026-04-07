"""
LinkBypass Pro — Layer 3: External Bypass API Services + Self-Hosted API
=========================================================================
Uses multiple real bypass API services + our own self-hosted bypass API.
Includes adaptive ranking based on success rates.
"""

import logging
import json
import random
import time
import re
from typing import Optional, List
from urllib.parse import quote, urlparse

import httpx

from bot.config import API_TIMEOUT, USER_AGENTS
from bot.engine.url_utils import is_valid_url, get_domain

logger = logging.getLogger(__name__)


class BypassAPI:
    """Base bypass API class with stats tracking."""

    def __init__(self, name: str, priority: int = 5):
        self.name = name
        self.priority = priority
        self.success_count = 0
        self.fail_count = 0

    async def bypass(self, url: str) -> Optional[str]:
        raise NotImplementedError

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.fail_count
        return self.success_count / total if total > 0 else 0.5


class SelfHostedAPI(BypassAPI):
    """Uses curl_cffi with TLS fingerprinting for direct CF bypass."""

    def __init__(self):
        super().__init__("self-hosted", priority=0)

    async def bypass(self, url: str) -> Optional[str]:
        try:
            from curl_cffi.requests import AsyncSession
        except ImportError:
            return None

        domain = get_domain(url)

        for profile in ["chrome124", "chrome120", "chrome116", "safari17_0"]:
            try:
                async with AsyncSession(impersonate=profile, timeout=API_TIMEOUT, verify=False) as session:
                    resp = await session.get(
                        url,
                        headers={
                            'User-Agent': random.choice(USER_AGENTS),
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                            'Accept-Language': 'en-US,en;q=0.9',
                            'Sec-Ch-Ua': '"Chromium";v="124", "Google Chrome";v="124"',
                            'Sec-Ch-Ua-Mobile': '?0',
                            'Sec-Ch-Ua-Platform': '"Windows"',
                            'Upgrade-Insecure-Requests': '1',
                            'Sec-Fetch-Dest': 'document',
                            'Sec-Fetch-Mode': 'navigate',
                            'Sec-Fetch-Site': 'none',
                            'Sec-Fetch-User': '?1',
                        },
                        allow_redirects=True,
                        max_redirects=10,
                    )

                    final = str(resp.url)
                    if get_domain(final) != domain and is_valid_url(final):
                        self.success_count += 1
                        return final

                    if resp.status_code == 200:
                        html = resp.text
                        for pat in [
                            r'window\.location(?:\.href)?\s*=\s*["\'"](https?://[^"\']+)["\'""]',
                            r'location\.replace\(["\'"](https?://[^"\']+)["\'""]',
                            r'<meta[^>]+url=(https?://[^"\'>]+)',
                            r'"(?:url|link|destination|redirect)"\s*:\s*"(https?://[^"]+)"',
                            r'href=["\'"](https?://[^"\'\s]+)["\'""].*?(?:btn|button|continue|go|visit)',
                        ]:
                            m = re.search(pat, html, re.IGNORECASE)
                            if m and get_domain(m.group(1)) != domain:
                                self.success_count += 1
                                return m.group(1)

                    if resp.status_code == 403:
                        continue

            except Exception:
                continue

        self.fail_count += 1
        return None


class RapidAPIBypass(BypassAPI):
    """Use free bypass APIs available online."""

    def __init__(self):
        super().__init__("rapid-bypass", priority=1)

    async def bypass(self, url: str) -> Optional[str]:
        endpoints = [
            {
                "url": "https://api.bypass.vip/bypass",
                "method": "POST",
                "json": {"url": url},
                "keys": ["destination", "result", "bypassed", "url"],
            },
            {
                "url": f"https://api.emilyx.in/bypass?url={quote(url)}",
                "method": "GET",
                "keys": ["result", "bypassed_link", "url", "destination"],
            },
            {
                "url": "https://bypass.pm/bypass2",
                "method": "POST",
                "form": {"url": url},
                "keys": ["destination", "result", "url"],
            },
        ]

        for ep in endpoints:
            try:
                async with httpx.AsyncClient(timeout=API_TIMEOUT, verify=False) as client:
                    headers = {
                        'User-Agent': random.choice(USER_AGENTS),
                        'Accept': 'application/json',
                    }

                    if ep["method"] == "POST":
                        if "json" in ep:
                            resp = await client.post(ep["url"], json=ep["json"], headers=headers)
                        else:
                            resp = await client.post(ep["url"], data=ep.get("form", {}), headers=headers)
                    else:
                        resp = await client.get(ep["url"], headers=headers)

                    if resp.status_code == 200:
                        try:
                            data = resp.json()
                            if isinstance(data, dict):
                                for key in ep["keys"]:
                                    val = data.get(key)
                                    if isinstance(val, str) and is_valid_url(val):
                                        self.success_count += 1
                                        return val
                                for k in ['data', 'response']:
                                    if isinstance(data.get(k), dict):
                                        for key in ['url', 'link', 'destination', 'result']:
                                            val = data[k].get(key)
                                            if isinstance(val, str) and is_valid_url(val):
                                                self.success_count += 1
                                                return val
                        except Exception:
                            pass

            except Exception as e:
                logger.debug(f"[Layer3] {ep['url'][:40]} error: {e}")
                continue

        self.fail_count += 1
        return None


class AdLinkFlyDirectAPI(BypassAPI):
    """
    Direct AdLinkFly bypass using curl_cffi — handles the full
    AdLinkFly flow (GET page -> extract token -> POST to /links/go).
    """

    def __init__(self):
        super().__init__("adlinkfly-direct", priority=1)

    async def bypass(self, url: str) -> Optional[str]:
        domain = get_domain(url)

        try:
            from curl_cffi.requests import AsyncSession
            from bot.engine.url_utils import extract_csrf_token, extract_hidden_inputs

            parsed = urlparse(url)
            base = f"{parsed.scheme}://{parsed.netloc}"
            alias = parsed.path.strip('/').split('/')[-1]

            async with AsyncSession(impersonate="chrome124", timeout=API_TIMEOUT, verify=False) as s:
                h = {
                    'User-Agent': random.choice(USER_AGENTS),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Upgrade-Insecure-Requests': '1',
                    'Referer': 'https://www.google.com/',
                }

                resp = await s.get(url, headers=h)

                if resp.status_code == 403:
                    return None

                final = str(resp.url)
                if get_domain(final) != domain and is_valid_url(final):
                    self.success_count += 1
                    return final

                if resp.status_code != 200:
                    return None

                html = resp.text
                csrf = extract_csrf_token(html)
                hidden = extract_hidden_inputs(html)

                ajax_h = h.copy()
                ajax_h.update({
                    'Accept': 'application/json, */*',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'Origin': base,
                    'Referer': url,
                    'Sec-Fetch-Dest': 'empty',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'same-origin',
                })

                payloads = []
                if hidden:
                    p = hidden.copy()
                    if csrf:
                        p['_token'] = csrf
                    payloads.append(p)
                if csrf:
                    payloads.append({'_token': csrf, 'alias': alias})
                    payloads.append({'_token': csrf, 'id': alias})
                payloads.append({'alias': alias})

                for go in [f'{base}/links/go', f'{base}/link/go']:
                    for payload in payloads:
                        try:
                            r2 = await s.post(go, data=payload, headers=ajax_h)
                            result = self._parse(r2, domain)
                            if result:
                                self.success_count += 1
                                return result
                        except Exception:
                            continue

                if hidden or csrf:
                    fd = (hidden or {}).copy()
                    if csrf:
                        fd['_token'] = csrf
                    try:
                        r3 = await s.post(url, data=fd, headers={
                            **h, 'Origin': base, 'Referer': url,
                            'Content-Type': 'application/x-www-form-urlencoded',
                        })
                        result = self._parse(r3, domain)
                        if result:
                            self.success_count += 1
                            return result
                    except Exception:
                        pass

        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"[Layer3] adlinkfly-direct error: {e}")

        self.fail_count += 1
        return None

    def _parse(self, resp, domain: str) -> Optional[str]:
        if not resp:
            return None
        if resp.status_code in (301, 302, 303, 307, 308):
            loc = resp.headers.get('location', '')
            if loc and is_valid_url(loc) and get_domain(loc) != domain:
                return loc
        final = str(resp.url)
        if get_domain(final) != domain and is_valid_url(final):
            return final
        if resp.status_code != 200:
            return None
        text = resp.text.strip()
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                for k in ['url', 'link', 'destination', 'redirect', 'result',
                           'destination_url', 'go_url', 'target', 'final_url']:
                    v = data.get(k)
                    if isinstance(v, str) and is_valid_url(v) and get_domain(v) != domain:
                        return v
        except Exception:
            pass
        if is_valid_url(text) and get_domain(text) != domain:
            return text
        for u in re.findall(r'https?://[^\s"\'<>]+', text[:5000]):
            u = u.rstrip('.,;:)')
            if is_valid_url(u) and get_domain(u) != domain:
                return u
        return None


class GenericUnshortenerAPI(BypassAPI):
    """Generic unshortener for simple redirect shorteners."""

    def __init__(self):
        super().__init__("unshorten", priority=5)

    async def bypass(self, url: str) -> Optional[str]:
        try:
            async with httpx.AsyncClient(timeout=15, verify=False, follow_redirects=True, max_redirects=15) as client:
                resp = await client.head(url, headers={
                    'User-Agent': random.choice(USER_AGENTS),
                })
                final = str(resp.url)
                if final != url and is_valid_url(final):
                    self.success_count += 1
                    return final
        except Exception:
            pass
        self.fail_count += 1
        return None


# Initialize APIs
_apis: List[BypassAPI] = [
    SelfHostedAPI(),
    AdLinkFlyDirectAPI(),
    RapidAPIBypass(),
    GenericUnshortenerAPI(),
]


async def attempt(url: str) -> Optional[str]:
    """Try all APIs in priority order (adaptive ranking)."""
    logger.info(f"[Layer3] Trying {len(_apis)} APIs for: {url[:80]}")

    sorted_apis = sorted(_apis, key=lambda a: (-a.success_rate, a.priority))

    for api in sorted_apis:
        logger.debug(f"[Layer3] Trying {api.name}")
        try:
            result = await api.bypass(url)
            if result:
                logger.info(f"[Layer3] {api.name} succeeded: {result[:80]}")
                return result
        except Exception as e:
            logger.debug(f"[Layer3] {api.name} error: {e}")

    return None


# Alias for manager.py import
try_external_apis = attempt


def get_api_stats() -> List[dict]:
    return [
        {
            'name': api.name,
            'priority': api.priority,
            'success_count': api.success_count,
            'fail_count': api.fail_count,
            'success_rate': f"{api.success_rate:.0%}",
        }
        for api in _apis
    ]

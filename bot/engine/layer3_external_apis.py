"""
LinkBypass Pro — Layer 3: External Bypass API Services
=======================================================
Uses multiple external bypass API services as a fallback when
local pattern-based bypass fails. Tries APIs in priority order
with automatic failover.

Supported APIs:
1. linkbypass.lol — Primary free API (curl_cffi for TLS fingerprinting)
2. bypass.vip — Secondary API
3. adbypass.org — Tertiary API
4. Social Unlock APIs — For social-locker sites
5. Custom configured APIs via admin panel
"""

import logging
import json
import random
import time
import re
from typing import Optional, Dict, List, Tuple
from urllib.parse import quote, urlencode

import httpx

from bot.config import (
    API_TIMEOUT, USER_AGENTS, LINKBYPASS_API_KEY,
    BYPASS_VIP_API_KEY, ADBYPASS_API_KEY
)
from bot.engine.url_utils import is_valid_url, get_domain
from bot.database.db import log_api_usage

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API Definitions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class BypassAPI:
    """Represents an external bypass API service."""

    def __init__(self, name: str, priority: int = 5):
        self.name = name
        self.priority = priority
        self.success_count = 0
        self.fail_count = 0
        self.last_success = 0
        self.last_failure = 0

    async def bypass(self, url: str) -> Optional[str]:
        raise NotImplementedError

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.fail_count
        if total == 0:
            return 0.5  # Unknown
        return self.success_count / total


class LinkBypassLolAPI(BypassAPI):
    """linkbypass.lol — Primary bypass API with browser-like TLS fingerprinting."""

    def __init__(self):
        super().__init__("linkbypass.lol", priority=1)
        self.base_url = "https://linkbypass.lol"

    async def bypass(self, url: str) -> Optional[str]:
        start = time.time()
        try:
            # Try with curl_cffi first for better TLS fingerprinting
            try:
                from curl_cffi.requests import AsyncSession
                async with AsyncSession(impersonate="chrome124") as session:
                    # Step 1: Get token
                    resp = await session.get(
                        self.base_url,
                        headers={
                            'User-Agent': random.choice(USER_AGENTS),
                            'Accept': 'text/html,application/xhtml+xml',
                            'Referer': 'https://www.google.com/',
                        },
                        timeout=API_TIMEOUT
                    )
                    token = None
                    token_match = re.search(
                        r'name=["\']_token["\'][^>]*value=["\']([^"\']+)["\']',
                        resp.text
                    )
                    if token_match:
                        token = token_match.group(1)

                    # Step 2: Submit URL for bypass
                    data = {"url": url}
                    if token:
                        data["_token"] = token

                    # Try JSON API endpoint first
                    api_resp = await session.post(
                        f"{self.base_url}/bypass",
                        json={"url": url},
                        headers={
                            'Content-Type': 'application/json',
                            'Accept': 'application/json',
                            'X-Requested-With': 'XMLHttpRequest',
                            'Referer': self.base_url,
                        },
                        timeout=API_TIMEOUT
                    )

                    elapsed = (time.time() - start) * 1000
                    result = self._parse_response(api_resp.text, api_resp.status_code)
                    if result:
                        self.success_count += 1
                        self.last_success = time.time()
                        await log_api_usage(self.name, "/bypass", api_resp.status_code, elapsed, True)
                        return result

                    # Try form POST
                    form_resp = await session.post(
                        self.base_url,
                        data=data,
                        headers={
                            'Content-Type': 'application/x-www-form-urlencoded',
                            'Referer': self.base_url,
                        },
                        timeout=API_TIMEOUT
                    )
                    result = self._parse_response(form_resp.text, form_resp.status_code)
                    if result:
                        self.success_count += 1
                        await log_api_usage(self.name, "/form", form_resp.status_code, elapsed, True)
                        return result

            except ImportError:
                logger.debug("[Layer3] curl_cffi not available, using httpx")

            # Fallback to httpx
            async with httpx.AsyncClient(timeout=API_TIMEOUT, verify=False) as client:
                headers = {
                    'User-Agent': random.choice(USER_AGENTS),
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                }

                resp = await client.post(
                    f"{self.base_url}/bypass",
                    json={"url": url},
                    headers=headers
                )

                elapsed = (time.time() - start) * 1000
                result = self._parse_response(resp.text, resp.status_code)
                if result:
                    self.success_count += 1
                    await log_api_usage(self.name, "/bypass", resp.status_code, elapsed, True)
                    return result

        except Exception as e:
            elapsed = (time.time() - start) * 1000
            self.fail_count += 1
            self.last_failure = time.time()
            await log_api_usage(self.name, "/bypass", 0, elapsed, False, str(e)[:200])
            logger.debug(f"[Layer3] {self.name} error: {e}")

        return None

    def _parse_response(self, text: str, status_code: int) -> Optional[str]:
        """Parse various response formats from linkbypass.lol."""
        if status_code != 200:
            return None

        # Try JSON
        try:
            data = json.loads(text)
            for key in ['destination', 'bypassed', 'result', 'url', 'link',
                        'bypassed_url', 'destination_url', 'final_url']:
                if key in data:
                    url = data[key]
                    if isinstance(url, str) and is_valid_url(url):
                        return url
            if 'data' in data and isinstance(data['data'], dict):
                for key in ['url', 'link', 'destination', 'result']:
                    if key in data['data'] and is_valid_url(str(data['data'][key])):
                        return data['data'][key]
        except (json.JSONDecodeError, TypeError):
            pass

        # Try finding URL in HTML
        urls = re.findall(r'https?://[^\s"\'<>]+', text)
        for u in urls:
            if is_valid_url(u) and not u.startswith('https://linkbypass'):
                return u

        return None


class BypassVipAPI(BypassAPI):
    """bypass.vip — Secondary bypass API."""

    def __init__(self):
        super().__init__("bypass.vip", priority=2)
        self.base_url = "https://bypass.vip"

    async def bypass(self, url: str) -> Optional[str]:
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=API_TIMEOUT, verify=False) as client:
                headers = {
                    'User-Agent': random.choice(USER_AGENTS),
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                }

                resp = await client.post(
                    f"{self.base_url}/api/bypass",
                    json={"url": url},
                    headers=headers
                )

                elapsed = (time.time() - start) * 1000

                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        result = data.get('result') or data.get('destination') or data.get('url')
                        if result and is_valid_url(str(result)):
                            self.success_count += 1
                            await log_api_usage(self.name, "/api/bypass", 200, elapsed, True)
                            return str(result)
                    except Exception:
                        pass

        except Exception as e:
            elapsed = (time.time() - start) * 1000
            self.fail_count += 1
            await log_api_usage(self.name, "/api/bypass", 0, elapsed, False, str(e)[:200])
            logger.debug(f"[Layer3] {self.name} error: {e}")

        return None


class AdBypassAPI(BypassAPI):
    """adbypass.org — General ad-link bypass API."""

    def __init__(self):
        super().__init__("adbypass.org", priority=3)
        self.base_url = "https://adbypass.org"

    async def bypass(self, url: str) -> Optional[str]:
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=API_TIMEOUT, verify=False) as client:
                headers = {
                    'User-Agent': random.choice(USER_AGENTS),
                    'Accept': 'application/json',
                }

                resp = await client.get(
                    f"{self.base_url}/bypass",
                    params={"url": url},
                    headers=headers
                )

                elapsed = (time.time() - start) * 1000

                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        result = data.get('bypassed') or data.get('destination') or data.get('url')
                        if result and is_valid_url(str(result)):
                            self.success_count += 1
                            await log_api_usage(self.name, "/bypass", 200, elapsed, True)
                            return str(result)
                    except Exception:
                        pass

        except Exception as e:
            elapsed = (time.time() - start) * 1000
            self.fail_count += 1
            await log_api_usage(self.name, "/bypass", 0, elapsed, False, str(e)[:200])
            logger.debug(f"[Layer3] {self.name} error: {e}")

        return None


class BypassRocksAPI(BypassAPI):
    """bypass.rocks — Community bypass API."""

    def __init__(self):
        super().__init__("bypass.rocks", priority=4)
        self.base_url = "https://bypass.rocks"

    async def bypass(self, url: str) -> Optional[str]:
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=API_TIMEOUT, verify=False) as client:
                headers = {
                    'User-Agent': random.choice(USER_AGENTS),
                    'Accept': 'application/json',
                }
                resp = await client.post(
                    f"{self.base_url}/bypass",
                    json={"url": url},
                    headers=headers
                )
                elapsed = (time.time() - start) * 1000
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        result = data.get('destination') or data.get('result') or data.get('url')
                        if result and is_valid_url(str(result)):
                            self.success_count += 1
                            await log_api_usage(self.name, "/bypass", 200, elapsed, True)
                            return str(result)
                    except Exception:
                        pass
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            self.fail_count += 1
            await log_api_usage(self.name, "/bypass", 0, elapsed, False, str(e)[:200])
        return None


class GenericUnshortenerAPI(BypassAPI):
    """Generic unshortener API — works for simple redirect shorteners."""

    def __init__(self):
        super().__init__("unshorten.me", priority=5)

    async def bypass(self, url: str) -> Optional[str]:
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=15, verify=False) as client:
                # Try unshorten.it API
                resp = await client.post(
                    "https://unshorten.it/api/v2/unshorten",
                    json={"url": url},
                    headers={
                        'User-Agent': random.choice(USER_AGENTS),
                        'Accept': 'application/json',
                    }
                )
                elapsed = (time.time() - start) * 1000
                if resp.status_code == 200:
                    data = resp.json()
                    result = data.get('unshortened_url') or data.get('url')
                    if result and is_valid_url(str(result)) and str(result) != url:
                        self.success_count += 1
                        await log_api_usage(self.name, "/unshorten", 200, elapsed, True)
                        return str(result)
        except Exception as e:
            logger.debug(f"[Layer3] unshorten.me error: {e}")
        return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API Manager
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Initialize all APIs
_apis: List[BypassAPI] = [
    LinkBypassLolAPI(),
    BypassVipAPI(),
    AdBypassAPI(),
    BypassRocksAPI(),
    GenericUnshortenerAPI(),
]


async def attempt(url: str) -> Optional[str]:
    """
    Try all external bypass APIs in priority order.
    Returns the first successful result.
    """
    logger.info(f"[Layer3] Trying {len(_apis)} external APIs for: {url[:80]}")

    # Sort by success rate, then priority
    sorted_apis = sorted(
        _apis,
        key=lambda a: (-a.success_rate, a.priority)
    )

    for api in sorted_apis:
        logger.debug(f"[Layer3] Trying {api.name} (success rate: {api.success_rate:.0%})")
        result = await api.bypass(url)
        if result:
            logger.info(f"[Layer3] {api.name} succeeded: {result[:80]}")
            return result
        logger.debug(f"[Layer3] {api.name} returned no result")

    return None


def get_api_stats() -> List[dict]:
    """Get statistics for all APIs."""
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

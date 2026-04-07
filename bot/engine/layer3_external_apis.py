"""
LinkBypass Pro — Layer 3: External Bypass APIs + Self-Hosted Engine v4.0
=========================================================================
Multi-strategy bypass using 10+ external API services, curl_cffi TLS
fingerprinting, and intelligent AdLinkFly flow automation.
"""

import logging
import json
import random
import time
import re
import asyncio
import hashlib
from typing import Optional, List, Dict
from urllib.parse import quote, urlparse, urljoin

import httpx

from bot.config import API_TIMEOUT, USER_AGENTS
from bot.engine.url_utils import is_valid_url, get_domain, extract_csrf_token, extract_hidden_inputs

logger = logging.getLogger(__name__)

# ── Blocklist: never return these as "bypassed" URLs ──────
BLOCKLIST_DOMAINS = {
    'cloudflare.com', 'challenges.cloudflare.com', 'google.com',
    'gstatic.com', 'googleapis.com', 'facebook.com', 'fbcdn.net',
    'doubleclick.net', 'googlesyndication.com', 'googleadservices.com',
    'adsense.com', 'analytics.google.com', 'cdn.jsdelivr.net',
    'jquery.com', 'bootstrapcdn.com', 'cloudflareinsights.com',
}

def _is_valid_destination(url: str, source_domain: str) -> bool:
    """Validate that a URL is a real destination, not junk."""
    if not url or not is_valid_url(url):
        return False
    dest = get_domain(url)
    if not dest or dest == source_domain:
        return False
    if dest in BLOCKLIST_DOMAINS:
        return False
    if any(bl in dest for bl in ['cloudflare', 'google-analytics', 'adsense', 'doubleclick']):
        return False
    if len(url) < 10:
        return False
    return True


class BypassAPI:
    """Base class with stats tracking."""

    def __init__(self, name: str, priority: int = 5):
        self.name = name
        self.priority = priority
        self.successes = 0
        self.failures = 0
        self.last_success = 0

    async def bypass(self, url: str) -> Optional[str]:
        raise NotImplementedError

    def score(self) -> float:
        total = self.successes + self.failures
        rate = self.successes / total if total > 0 else 0.5
        recency = min(1.0, (time.time() - self.last_success) / 3600) if self.last_success else 0.5
        return rate * 0.7 + (1 - recency) * 0.3

    def _record_success(self):
        self.successes += 1
        self.last_success = time.time()

    def _record_failure(self):
        self.failures += 1


class MultiEndpointAPI(BypassAPI):
    """Tries 10+ free bypass API services."""

    def __init__(self):
        super().__init__("multi-api", priority=1)

    async def bypass(self, url: str) -> Optional[str]:
        source_domain = get_domain(url)
        encoded = quote(url, safe='')

        endpoints = [
            {"url": "https://api.bypass.vip/bypass", "method": "POST",
             "json": {"url": url}, "keys": ["destination", "result", "bypassed", "url"]},
            {"url": "https://bypass.pm/bypass2", "method": "POST",
             "form": {"url": url}, "keys": ["destination", "result", "url"]},
            {"url": f"https://api.emilyx.in/bypass?url={encoded}", "method": "GET",
             "keys": ["result", "bypassed_link", "url", "destination"]},
            {"url": f"https://adbypass.org/bypass?url={encoded}", "method": "GET",
             "keys": ["bypassed", "destination", "result", "url"]},
            {"url": "https://short-link-bypass.vercel.app/bypass", "method": "POST",
             "json": {"url": url}, "keys": ["bypass", "destination", "result"]},
            {"url": f"https://api.thebypasser.com/bypass?url={encoded}", "method": "GET",
             "keys": ["result", "bypassed", "destination", "url"]},
            {"url": "https://bypass.bot/bypass", "method": "POST",
             "json": {"url": url, "type": "auto"}, "keys": ["destination", "result", "bypass", "url"]},
            {"url": f"https://bypass-api.vercel.app/api/bypass?url={encoded}", "method": "GET",
             "keys": ["result", "destination", "url", "bypassed"]},
            {"url": f"https://bypass-api-gold.vercel.app/bypass?url={encoded}", "method": "GET",
             "keys": ["result", "destination", "url"]},
            {"url": f"https://relayo.com/api/bypass?link={encoded}", "method": "GET",
             "keys": ["url", "result", "destination", "link"]},
        ]

        random.shuffle(endpoints)

        async with httpx.AsyncClient(timeout=API_TIMEOUT, verify=False) as client:
            for ep in endpoints:
                try:
                    if ep["method"] == "POST":
                        kwargs = {}
                        if "json" in ep:
                            kwargs["json"] = ep["json"]
                        elif "form" in ep:
                            kwargs["data"] = ep["form"]
                        resp = await client.post(ep["url"], **kwargs)
                    else:
                        resp = await client.get(ep["url"])

                    if resp.status_code != 200:
                        continue

                    result = self._extract_url(resp.text, ep.get("keys", []), source_domain)
                    if result:
                        self._record_success()
                        logger.info(f"[Layer3] {ep['url'][:40]} -> {result[:80]}")
                        return result

                except Exception as e:
                    logger.debug(f"[Layer3] {ep.get('url','')[:40]} err: {e}")
                    continue

        self._record_failure()
        return None

    def _extract_url(self, text: str, keys: list, source_domain: str) -> Optional[str]:
        try:
            data = json.loads(text.strip())
        except Exception:
            text = text.strip()
            if _is_valid_destination(text, source_domain):
                return text
            return None

        if not isinstance(data, dict):
            return None

        for key in keys:
            val = data.get(key)
            if isinstance(val, str) and _is_valid_destination(val, source_domain):
                return val

        for k in ['data', 'response', 'result']:
            nested = data.get(k)
            if isinstance(nested, dict):
                for key in ['url', 'link', 'destination', 'result', 'bypassed']:
                    val = nested.get(key)
                    if isinstance(val, str) and _is_valid_destination(val, source_domain):
                        return val
            elif isinstance(nested, str) and _is_valid_destination(nested, source_domain):
                return nested

        for v in data.values():
            if isinstance(v, str) and _is_valid_destination(v, source_domain):
                return v

        return None


class CurlCffiEngine(BypassAPI):
    """Direct CF bypass via curl_cffi TLS fingerprinting."""

    def __init__(self):
        super().__init__("curl-cffi", priority=0)

    async def bypass(self, url: str) -> Optional[str]:
        try:
            from curl_cffi.requests import AsyncSession
        except ImportError:
            return None

        source_domain = get_domain(url)
        profiles = ["chrome124", "chrome120", "safari17_0", "edge101", "chrome116"]

        for profile in profiles:
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
                    if _is_valid_destination(final, source_domain):
                        self._record_success()
                        return final

                    if resp.status_code == 200:
                        html = resp.text
                        dest = self._extract_from_html(html, source_domain)
                        if dest:
                            self._record_success()
                            return dest

                        dest = await self._try_adlinkfly(session, url, html, source_domain)
                        if dest:
                            self._record_success()
                            return dest

                    if resp.status_code == 403:
                        continue

            except Exception:
                continue

        self._record_failure()
        return None

    def _extract_from_html(self, html: str, source_domain: str) -> Optional[str]:
        patterns = [
            r'window\.location(?:\.href)?\s*=\s*["\'](https?://[^"\' ]+)[\"\']',
            r'location\.replace\(["\'](https?://[^"\' ]+)[\"\']',
            r'<meta[^>]+url=(https?://[^"\'>]+)',
            r'"(?:url|link|destination|redirect)"\s*:\s*"(https?://[^"]+)"',
            r'href=["\'](https?://[^"\'\s]+)[\"\'].*?(?:btn|button|continue|go|visit)',
        ]
        for pat in patterns:
            m = re.search(pat, html, re.IGNORECASE)
            if m and _is_valid_destination(m.group(1), source_domain):
                return m.group(1)
        return None

    async def _try_adlinkfly(self, session, url: str, html: str, source_domain: str) -> Optional[str]:
        """Handle AdLinkFly CMS flow."""
        try:
            csrf = extract_csrf_token(html)
            hidden = extract_hidden_inputs(html)

            if not csrf and not hidden:
                return None

            parsed = urlparse(url)
            go_url = f"{parsed.scheme}://{parsed.netloc}/links/go"

            form_data = {**hidden}
            if csrf:
                form_data['_token'] = csrf
                form_data['_csrfToken'] = csrf

            resp = await session.post(
                go_url,
                data=form_data,
                headers={
                    'Referer': url,
                    'Origin': f"{parsed.scheme}://{parsed.netloc}",
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                allow_redirects=True,
                max_redirects=10,
            )

            final = str(resp.url)
            if _is_valid_destination(final, source_domain):
                return final

            if resp.status_code == 200:
                dest = self._extract_from_html(resp.text, source_domain)
                if dest:
                    return dest

        except Exception as e:
            logger.debug(f"[Layer3] AdLinkFly flow failed: {e}")

        return None


_apis: List[BypassAPI] = []

def _get_apis() -> List[BypassAPI]:
    global _apis
    if not _apis:
        _apis = [
            CurlCffiEngine(),
            MultiEndpointAPI(),
        ]
    return _apis


async def attempt(url: str) -> Optional[str]:
    """Try all external API services, ranked by score."""
    apis = sorted(_get_apis(), key=lambda a: a.score(), reverse=True)

    for api in apis:
        try:
            result = await asyncio.wait_for(api.bypass(url), timeout=API_TIMEOUT + 5)
            if result and is_valid_url(result):
                logger.info(f"[Layer3] {api.name} bypassed: {result[:80]}")
                return result
        except asyncio.TimeoutError:
            logger.debug(f"[Layer3] {api.name} timed out")
            api._record_failure()
        except Exception as e:
            logger.debug(f"[Layer3] {api.name} error: {e}")
            api._record_failure()

    return None


def get_api_stats() -> Dict:
    """Return stats for admin panel."""
    return {
        api.name: {
            "successes": api.successes,
            "failures": api.failures,
            "score": round(api.score(), 3),
        }
        for api in _get_apis()
    }

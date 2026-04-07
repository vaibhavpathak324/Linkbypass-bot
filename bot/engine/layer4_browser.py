"""
LinkBypass Pro — Layer 4: Advanced Cloudflare Bypass
=====================================================
Uses curl_cffi (JA3/TLS fingerprinting) + cloudscraper for
Cloudflare-protected shorteners like lksfy.com.

Strategies:
1. curl_cffi with Chrome/Safari/Edge impersonation
2. cloudscraper with JS challenge solving
3. Multi-header rotation to mimic real browsers
"""

import re
import asyncio
import logging
import random
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ── Real browser headers ─────────────────────────────────────

CHROME_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "max-age=0",
    "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

SAFARI_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

EDGE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Sec-Ch-Ua": '"Microsoft Edge";v="122", "Chromium";v="122", "Not(A:Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

# Patterns to find destination URLs in page content
DESTINATION_PATTERNS = [
    r'href=["\'](https?://[^"\'\s]+)["\']\s*(?:id|class)=["\'].*?(?:btn|button|download|continue|redirect|go|visit|proceed)',
    r'window\.location(?:\.href)?\s*=\s*["\'"](https?://[^"\']+)["\']',
    r'window\.open\s*\(["\'"](https?://[^"\']+)["\']',
    r'<meta\s+http-equiv=["\']refresh["\']\s+content=["\']\d+;\s*url=(https?://[^"\']+)["\']',
    r'location\.replace\s*\(["\'"](https?://[^"\']+)["\']',
    r'var\s+(?:url|link|dest|redirect|target)\s*=\s*["\'"](https?://[^"\']+)["\']',
    r'data-(?:url|href|link|redirect)=["\'](https?://[^"\'\s]+)["\']',
    r'"(?:url|link|destination|redirect)"\s*:\s*"(https?://[^"]+)"',
]


def _extract_destination(html: str, source_domain: str) -> Optional[str]:
    """Extract destination URL from page HTML."""
    for pattern in DESTINATION_PATTERNS:
        try:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                parsed = urlparse(match)
                if parsed.netloc and parsed.netloc != source_domain:
                    return match
        except re.error:
            continue
    return None


async def _try_curl_cffi(url: str) -> Optional[str]:
    """Use curl_cffi to bypass Cloudflare with TLS fingerprinting."""
    try:
        from curl_cffi.requests import AsyncSession
    except ImportError:
        logger.warning("curl_cffi not installed, skipping")
        return None

    domain = urlparse(url).netloc
    impersonations = ["chrome122", "chrome120", "chrome119", "safari17_0", "edge101"]

    for imp in impersonations[:3]:  # Try up to 3
        try:
            async with AsyncSession(impersonate=imp) as session:
                resp = await session.get(url, allow_redirects=True, timeout=15)

                # Check if we got redirected to destination
                final_url = str(resp.url)
                final_domain = urlparse(final_url).netloc
                if final_domain != domain:
                    logger.info(f"curl_cffi ({imp}) redirect → {final_url}")
                    return final_url

                # Try to extract from HTML
                if resp.status_code == 200:
                    dest = _extract_destination(resp.text, domain)
                    if dest:
                        logger.info(f"curl_cffi ({imp}) extracted → {dest}")
                        return dest

        except Exception as e:
            logger.debug(f"curl_cffi {imp} failed: {e}")
            continue

    return None


async def _try_cloudscraper(url: str) -> Optional[str]:
    """Use cloudscraper to solve JS challenges."""
    try:
        import cloudscraper
    except ImportError:
        logger.warning("cloudscraper not installed, skipping")
        return None

    domain = urlparse(url).netloc

    def _scrape():
        scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "desktop": True},
            delay=5,
        )
        # Add realistic headers
        headers = random.choice([CHROME_HEADERS, EDGE_HEADERS])
        scraper.headers.update(headers)

        resp = scraper.get(url, allow_redirects=True, timeout=20)

        # Check redirect
        final_url = resp.url
        final_domain = urlparse(final_url).netloc
        if final_domain != domain:
            return final_url

        # Extract from content
        if resp.status_code == 200:
            return _extract_destination(resp.text, domain)

        return None

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _scrape)


async def _try_aiohttp_with_cf_cookies(url: str) -> Optional[str]:
    """Use aiohttp with pre-obtained CF clearance cookies."""
    try:
        import aiohttp
    except ImportError:
        return None

    domain = urlparse(url).netloc
    headers = {**random.choice([CHROME_HEADERS, SAFARI_HEADERS, EDGE_HEADERS]),
               "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                final_url = str(resp.url)
                final_domain = urlparse(final_url).netloc
                if final_domain != domain:
                    return final_url

                if resp.status == 200:
                    text = await resp.text()
                    return _extract_destination(text, domain)
    except Exception as e:
        logger.debug(f"aiohttp CF attempt failed: {e}")

    return None


async def try_cloudscraper_bypass(url: str) -> Optional[str]:
    """Main entry point for Layer 4 — tries all CF bypass strategies."""
    logger.info(f"[Layer4] Starting CF bypass for {url}")

    strategies = [
        ("curl_cffi", _try_curl_cffi),
        ("cloudscraper", _try_cloudscraper),
        ("aiohttp_cf", _try_aiohttp_with_cf_cookies),
    ]

    for name, strategy in strategies:
        try:
            result = await asyncio.wait_for(strategy(url), timeout=20)
            if result:
                logger.info(f"[Layer4] {name} succeeded → {result}")
                return result
        except asyncio.TimeoutError:
            logger.warning(f"[Layer4] {name} timed out")
        except Exception as e:
            logger.warning(f"[Layer4] {name} error: {e}")

    logger.info("[Layer4] All strategies failed")
    return None

# Alias for manager.py import
attempt = try_cloudscraper_bypass

"""
LinkBypass Pro — Layer 5: Ultra-Advanced Multi-Strategy Bypass
===============================================================
Last-resort layer combining:
1. Multi-profile TLS rotation with curl_cffi
2. cloudscraper with JS challenge solving
3. Multi-step AdLinkFly flow with delay simulation
4. DOM parsing and JS extraction
"""

import re
import json
import asyncio
import logging
import random
import time
from typing import Optional
from urllib.parse import urlparse, urljoin

logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────

def _is_dest(url: str, src_domain: str) -> bool:
    """Check if URL is a real destination (not same shortener)."""
    try:
        parsed = urlparse(url)
        return (
            parsed.scheme in ('http', 'https')
            and parsed.netloc
            and parsed.netloc != src_domain
            and not any(x in parsed.netloc for x in ['cloudflare', 'turnstile', 'challenges'])
        )
    except Exception:
        return False


def _extract_urls(html: str, src_domain: str) -> list:
    """Extract all candidate destination URLs from HTML."""
    patterns = [
        r'window\.location(?:\.href)?\s*=\s*["\'"](https?://[^"\']+)',
        r'location\.replace\(["\'"](https?://[^"\']+)',
        r'<meta[^>]+url=(https?://[^"\'>]+)',
        r'"(?:url|link|destination|redirect|go_url|final_url|target)"\s*:\s*"(https?://[^"]+)"',
        r'href=["\'"](https?://[^"\'\s]+)',
        r'window\.open\(["\'"](https?://[^"\']+)',
        r'data-(?:url|href|link|redirect)=["\'"](https?://[^"\'\s]+)',
        r'action=["\'"](https?://[^"\'\s]+)',
    ]
    urls = []
    for pat in patterns:
        try:
            for m in re.findall(pat, html, re.IGNORECASE):
                m = m.rstrip('.,;:)')
                if _is_dest(m, src_domain):
                    urls.append(m)
        except re.error:
            pass
    return urls


def _extract_adlinkfly_data(html: str) -> dict:
    """Extract AdLinkFly tokens and form data."""
    data = {}
    # CSRF token
    m = re.search(r'name=["\'"]_token["\'"]\s+value=["\'"](\w+)', html)
    if m:
        data['_token'] = m.group(1)
    m = re.search(r'<meta\s+name=["\'"]csrf-token["\'"]\s+content=["\'"](\w+)', html)
    if m:
        data['_token'] = m.group(1)
    # Hidden inputs
    for inp in re.findall(r'<input[^>]+type=["\'"]hidden["\'"][^>]*>', html, re.IGNORECASE):
        nm = re.search(r'name=["\'"](\w+)', inp)
        vl = re.search(r'value=["\'"](.*?)["\'"]', inp)
        if nm and vl:
            data[nm.group(1)] = vl.group(1)
    # Timer/wait value
    m = re.search(r'(?:timer|countdown|wait)\s*[:=]\s*(\d+)', html, re.IGNORECASE)
    if m:
        data['_wait'] = int(m.group(1))
    return data


async def _strategy_curl_multi(url: str) -> Optional[str]:
    """Strategy 1: curl_cffi multi-profile rotation."""
    try:
        from curl_cffi.requests import AsyncSession
    except ImportError:
        return None

    domain = urlparse(url).netloc
    profiles = ["chrome124", "chrome120", "chrome116", "safari17_0", "edge101"]
    random.shuffle(profiles)

    for profile in profiles[:4]:
        try:
            async with AsyncSession(impersonate=profile, timeout=20, verify=False) as s:
                h = {
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Cache-Control': 'max-age=0',
                    'Referer': 'https://www.google.com/',
                }

                resp = await s.get(url, headers=h, allow_redirects=True, max_redirects=10)

                final = str(resp.url)
                if _is_dest(final, domain):
                    return final

                if resp.status_code == 200:
                    html = resp.text

                    # Check for AdLinkFly pattern
                    adf = _extract_adlinkfly_data(html)
                    if adf.get('_token'):
                        wait = min(adf.pop('_wait', 3), 8)
                        await asyncio.sleep(wait)

                        parsed = urlparse(url)
                        base = f"{parsed.scheme}://{parsed.netloc}"
                        alias = parsed.path.strip('/').split('/')[-1]

                        ajax_h = {
                            **h,
                            'Accept': 'application/json, */*',
                            'X-Requested-With': 'XMLHttpRequest',
                            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                            'Origin': base,
                            'Referer': url,
                            'Sec-Fetch-Dest': 'empty',
                            'Sec-Fetch-Mode': 'cors',
                            'Sec-Fetch-Site': 'same-origin',
                        }

                        if 'alias' not in adf and 'id' not in adf:
                            adf['alias'] = alias

                        for go_url in [f'{base}/links/go', f'{base}/link/go']:
                            try:
                                r2 = await s.post(go_url, data=adf, headers=ajax_h)
                                f2 = str(r2.url)
                                if _is_dest(f2, domain):
                                    return f2
                                if r2.status_code == 200:
                                    try:
                                        jd = r2.json()
                                        for k in ['url', 'link', 'destination', 'redirect']:
                                            v = jd.get(k)
                                            if isinstance(v, str) and _is_dest(v, domain):
                                                return v
                                    except Exception:
                                        pass
                                if r2.status_code in (301, 302, 303, 307, 308):
                                    loc = r2.headers.get('location', '')
                                    if _is_dest(loc, domain):
                                        return loc
                            except Exception:
                                continue

                    # Generic extraction
                    candidates = _extract_urls(html, domain)
                    if candidates:
                        return candidates[0]

                if resp.status_code == 403:
                    continue

        except Exception as e:
            logger.debug(f"[Layer5] curl {profile} error: {e}")
            continue

    return None


async def _strategy_cloudscraper(url: str) -> Optional[str]:
    """Strategy 2: cloudscraper with JS challenge solving."""
    try:
        import cloudscraper
    except ImportError:
        return None

    domain = urlparse(url).netloc

    def _scrape():
        scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "desktop": True},
            delay=8,
        )
        scraper.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Referer': 'https://www.google.com/',
        })

        resp = scraper.get(url, allow_redirects=True, timeout=25)

        final = resp.url
        if _is_dest(final, domain):
            return final

        if resp.status_code == 200:
            html = resp.text

            # AdLinkFly flow
            adf = _extract_adlinkfly_data(html)
            if adf.get('_token'):
                wait = min(adf.pop('_wait', 3), 8)
                import time as _t
                _t.sleep(wait)

                parsed = urlparse(url)
                base = f"{parsed.scheme}://{parsed.netloc}"
                alias = parsed.path.strip('/').split('/')[-1]

                if 'alias' not in adf and 'id' not in adf:
                    adf['alias'] = alias

                for go_url in [f'{base}/links/go', f'{base}/link/go']:
                    try:
                        r2 = scraper.post(go_url, data=adf, headers={
                            'X-Requested-With': 'XMLHttpRequest',
                            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                            'Origin': base,
                            'Referer': url,
                        })
                        f2 = r2.url
                        if _is_dest(f2, domain):
                            return f2
                        if r2.status_code == 200:
                            try:
                                jd = r2.json()
                                for k in ['url', 'link', 'destination', 'redirect']:
                                    v = jd.get(k)
                                    if isinstance(v, str) and _is_dest(v, domain):
                                        return v
                            except Exception:
                                pass
                    except Exception:
                        continue

            candidates = _extract_urls(html, domain)
            if candidates:
                return candidates[0]

        return None

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _scrape)


async def _strategy_httpx_aggressive(url: str) -> Optional[str]:
    """Strategy 3: httpx with aggressive redirect following."""
    import httpx

    domain = urlparse(url).netloc
    ua = random.choice([
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    ])

    try:
        async with httpx.AsyncClient(
            timeout=20, verify=False, follow_redirects=True, max_redirects=20,
            headers={
                'User-Agent': ua,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
            }
        ) as client:
            resp = await client.get(url)
            final = str(resp.url)
            if _is_dest(final, domain):
                return final

            if resp.status_code == 200:
                candidates = _extract_urls(resp.text, domain)
                if candidates:
                    return candidates[0]
    except Exception:
        pass

    return None


async def attempt(url: str) -> Optional[str]:
    """Main entry: try all strategies in order."""
    logger.info(f"[Layer5] Starting advanced bypass for {url[:80]}")

    strategies = [
        ("curl_multi", _strategy_curl_multi),
        ("cloudscraper", _strategy_cloudscraper),
        ("httpx_aggressive", _strategy_httpx_aggressive),
    ]

    for name, func in strategies:
        try:
            logger.debug(f"[Layer5] Trying {name}")
            result = await asyncio.wait_for(func(url), timeout=25)
            if result:
                logger.info(f"[Layer5] {name} succeeded: {result[:80]}")
                return result
        except asyncio.TimeoutError:
            logger.warning(f"[Layer5] {name} timed out")
        except Exception as e:
            logger.warning(f"[Layer5] {name} error: {e}")

    logger.info("[Layer5] All strategies failed")
    return None


# Alias for manager.py import
try_headless_bypass = attempt

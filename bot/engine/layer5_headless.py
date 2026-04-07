"""
LinkBypass Pro - Layer 5: Stealth Playwright Browser v4.1
==========================================================
Real Chromium browser with Xvfb virtual display:
- Starts Xvfb on-demand for headed mode (beats CF detection)
- Falls back to headless if Xvfb unavailable
- CF managed challenge auto-wait (up to 45s)
- AdLinkFly flow automation (timer wait + button click)
- Network interception for destination URL detection
"""

import re
import os
import logging
import asyncio
import subprocess
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

BLOCKLIST_DOMAINS = {
    'cloudflare.com', 'challenges.cloudflare.com', 'google.com',
    'gstatic.com', 'googleapis.com', 'facebook.com', 'doubleclick.net',
    'googlesyndication.com', 'cloudflareinsights.com', 'cdn.jsdelivr.net',
    'jquery.com', 'bootstrapcdn.com', 'analytics.google.com',
    'adservice.google.com', 'pagead2.googlesyndication.com',
}

STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
Object.defineProperty(navigator, 'plugins', {get: () => {
    return [
        {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},
        {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
        {name: 'Native Client', filename: 'internal-nacl-plugin'},
    ];
}});
window.chrome = {
    runtime: {},
    loadTimes: function() { return {}; },
    csi: function() { return {}; },
    app: {isInstalled: false},
};
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
    Promise.resolve({state: Notification.permission}) :
    originalQuery(parameters)
);
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) return 'Intel Inc.';
    if (parameter === 37446) return 'Intel Iris OpenGL Engine';
    return getParameter.call(this, parameter);
};
Object.defineProperty(navigator, 'connection', {get: () => ({
    downlink: 10, effectiveType: '4g', onchange: null, rtt: 50, saveData: false
})});
Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
Object.defineProperty(navigator, 'maxTouchPoints', {get: () => 0});
Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
"""

_xvfb_proc = None
_xvfb_display = None

def _ensure_xvfb():
    """Start Xvfb if not already running. Returns True if display is available."""
    global _xvfb_proc, _xvfb_display

    # Already have a display?
    if os.environ.get('DISPLAY'):
        return True

    if _xvfb_proc and _xvfb_proc.poll() is None:
        os.environ['DISPLAY'] = _xvfb_display
        return True

    # Try to start Xvfb
    for display_num in range(99, 110):
        display = f":{display_num}"
        try:
            proc = subprocess.Popen(
                ['Xvfb', display, '-screen', '0', '1920x1080x24', '-nolisten', 'tcp'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            import time
            time.sleep(0.5)
            if proc.poll() is None:
                _xvfb_proc = proc
                _xvfb_display = display
                os.environ['DISPLAY'] = display
                logger.info(f"[Layer5] Started Xvfb on {display}")
                return True
        except FileNotFoundError:
            logger.debug("[Layer5] Xvfb not found, will use headless")
            return False
        except Exception:
            continue

    return False


def _is_dest(url: str, src_domain: str) -> bool:
    if not url:
        return False
    try:
        d = urlparse(url).netloc.lower().replace('www.', '')
        return bool(d and d != src_domain and d not in BLOCKLIST_DOMAINS
                     and not any(bl in d for bl in ['cloudflare', 'google-analytics', 'adsense']))
    except Exception:
        return False


async def _wait_for_cf(page, timeout_sec=45):
    """Wait for Cloudflare challenge to resolve."""
    for i in range(timeout_sec // 3):
        await page.wait_for_timeout(3000)
        title = await page.title()
        content = await page.content()

        if 'Just a moment' in title or 'challenge-platform' in content:
            logger.debug(f"[Layer5] CF challenge active (check {i+1})")
            # Try clicking CF turnstile checkbox in iframes
            try:
                for frame in page.frames:
                    try:
                        cb = await frame.query_selector('input[type="checkbox"]')
                        if cb:
                            await cb.click()
                            logger.info("[Layer5] Clicked CF turnstile checkbox")
                            await page.wait_for_timeout(3000)
                    except Exception:
                        pass
            except Exception:
                pass
            continue
        else:
            logger.info(f"[Layer5] CF resolved after {(i+1)*3}s")
            return True
    return False


async def attempt(url: str) -> Optional[str]:
    """Bypass using Playwright browser with Xvfb headed mode."""
    logger.info(f"[Layer5] Starting Playwright for: {url[:80]}")

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.warning("[Layer5] Playwright not installed")
        return None

    # Try headed mode via Xvfb, fall back to headless
    use_headed = _ensure_xvfb()
    logger.info(f"[Layer5] Mode: {'headed (Xvfb)' if use_headed else 'headless'}")

    original_domain = urlparse(url).netloc.lower().replace('www.', '')
    browser = None
    pw = None

    try:
        pw = await async_playwright().start()

        launch_args = [
            '--no-sandbox', '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-blink-features=AutomationControlled',
            '--disable-features=IsolateOrigins,site-per-process',
            '--window-size=1920,1080',
        ]
        if not use_headed:
            launch_args.append('--disable-gpu')

        browser = await pw.chromium.launch(
            headless=(not use_headed),
            args=launch_args
        )

        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='America/New_York',
            color_scheme='light',
            java_script_enabled=True,
            bypass_csp=True,
        )

        await context.add_init_script(STEALTH_SCRIPT)
        page = await context.new_page()

        destinations = []

        def on_response(response):
            try:
                resp_url = response.url
                if _is_dest(resp_url, original_domain):
                    destinations.append(resp_url)
            except Exception:
                pass

        page.on('response', on_response)

        try:
            response = await page.goto(url, wait_until='domcontentloaded', timeout=45000)
            logger.info(f"[Layer5] Load: status={response.status if response else '?'}, url={page.url[:80]}")

            if _is_dest(page.url, original_domain):
                return page.url

            # Handle CF challenge
            content = await page.content()
            title = await page.title()
            if 'Just a moment' in title or 'challenge-platform' in content:
                logger.info("[Layer5] CF challenge detected, waiting...")
                cf_ok = await _wait_for_cf(page, timeout_sec=45)
                if not cf_ok:
                    logger.warning("[Layer5] CF challenge did not resolve")

            if _is_dest(page.url, original_domain):
                return page.url

            # Post-CF: we should be on the shortener page
            await page.wait_for_timeout(2000)
            content = await page.content()
            logger.info(f"[Layer5] Page: title='{await page.title()}', url={page.url[:80]}")

            # Look for timer
            timer_match = re.search(r'var\s+(?:count|timer|countdown|seconds|wait|time)\s*=\s*(\d+)', content)
            if timer_match:
                wait_sec = min(int(timer_match.group(1)), 25)
                logger.info(f"[Layer5] Timer: {wait_sec}s")
                await page.wait_for_timeout(wait_sec * 1000 + 3000)
            else:
                await page.wait_for_timeout(8000)

            if _is_dest(page.url, original_domain):
                return page.url

            # Click buttons
            selectors = [
                '#btn-main', '#continue', '#bypass', '#get-link',
                '.get-link', '#link-button', '.link-button',
                'a.btn-primary', 'a.btn-success',
                'button.btn-primary', 'button.btn-success',
                '[id*="continue"]', '[id*="bypass"]', '[id*="getlink"]',
                'a[href*="go"]', 'a[href*="redirect"]',
                'input[type="submit"]', 'button[type="submit"]',
                '.btn-main', '#btn-go', '.btn-go',
                '#surl', '#skip', '.skip-btn', '#go-link', '.go-link',
            ]

            for sel in selectors:
                try:
                    els = await page.query_selector_all(sel)
                    for el in els:
                        if await el.is_visible():
                            logger.info(f"[Layer5] Clicking: {sel}")
                            await el.click()
                            await page.wait_for_timeout(4000)
                            if _is_dest(page.url, original_domain):
                                return page.url
                except Exception:
                    continue

            # Extract from HTML
            content = await page.content()
            patterns = [
                r'window\.location(?:\.href)?\s*=\s*["\'](https?://[^"\' ]+)["\']',
                r'location\.replace\(["\'](https?://[^"\' ]+)["\']',
                r'"(?:url|link|destination|redirect)"\s*:\s*"(https?://[^"]+)"',
                r'var\s+(?:url|link|dest|redirect)\s*=\s*["\'](https?://[^"\' ]+)["\']',
                r'data-(?:url|href)\s*=\s*["\'](https?://[^"\'\s]+)["\']',
            ]
            for pat in patterns:
                for m in re.finditer(pat, content, re.IGNORECASE):
                    if _is_dest(m.group(1), original_domain):
                        return m.group(1)

            if destinations:
                return destinations[-1]

            # Final wait loop
            for _ in range(3):
                await page.wait_for_timeout(5000)
                if _is_dest(page.url, original_domain):
                    return page.url
                if destinations:
                    return destinations[-1]
                for sel in selectors[:8]:
                    try:
                        el = await page.query_selector(sel)
                        if el and await el.is_visible():
                            await el.click()
                            await page.wait_for_timeout(3000)
                            if _is_dest(page.url, original_domain):
                                return page.url
                    except Exception:
                        continue

        except Exception as e:
            logger.warning(f"[Layer5] Nav error: {type(e).__name__}: {e}")

    except Exception as e:
        logger.error(f"[Layer5] Error: {type(e).__name__}: {e}")
    finally:
        try:
            if browser:
                await browser.close()
            if pw:
                await pw.stop()
        except Exception:
            pass

    return None

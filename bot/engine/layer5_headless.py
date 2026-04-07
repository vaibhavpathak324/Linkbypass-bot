"""
LinkBypass Pro - Layer 5: Stealth Playwright Browser v4.1
==========================================================
Real Chromium browser in HEADED mode via Xvfb with:
- Comprehensive anti-detection stealth patches
- CF managed challenge auto-wait (up to 45s)
- AdLinkFly flow automation (timer wait + button click)
- Network interception for destination URL detection
"""

import re
import logging
import asyncio
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
    runtime: {
        PlatformOs: {MAC: 'mac', WIN: 'win', ANDROID: 'android', CROS: 'cros', LINUX: 'linux', OPENBSD: 'openbsd'},
        PlatformArch: {ARM: 'arm', X86_32: 'x86-32', X86_64: 'x86-64', MIPS: 'mips', MIPS64: 'mips64'},
        PlatformNaclArch: {ARM: 'arm', X86_32: 'x86-32', X86_64: 'x86-64', MIPS: 'mips', MIPS64: 'mips64'},
        RequestUpdateCheckStatus: {THROTTLED: 'throttled', NO_UPDATE: 'no_update', UPDATE_AVAILABLE: 'update_available'},
        OnInstalledReason: {INSTALL: 'install', UPDATE: 'update', CHROME_UPDATE: 'chrome_update', SHARED_MODULE_UPDATE: 'shared_module_update'},
        OnRestartRequiredReason: {APP_UPDATE: 'app_update', OS_UPDATE: 'os_update', PERIODIC: 'periodic'},
    },
    loadTimes: function() { return {}; },
    csi: function() { return {}; },
    app: {isInstalled: false, InstallState: {INSTALLED: 'installed', NOT_INSTALLED: 'not_installed'}, RunningState: {RUNNING: 'running', CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run'}},
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
        content = await page.content()
        title = await page.title()

        # CF challenge indicators
        if 'Just a moment' in title or 'challenge-platform' in content or 'cf-browser-verification' in content:
            logger.debug(f"[Layer5] CF challenge still active (attempt {i+1})")
            # Try clicking the CF turnstile checkbox if visible
            try:
                frames = page.frames
                for frame in frames:
                    try:
                        checkbox = await frame.query_selector('input[type="checkbox"]')
                        if checkbox:
                            await checkbox.click()
                            logger.info("[Layer5] Clicked CF turnstile checkbox")
                            await page.wait_for_timeout(3000)
                    except Exception:
                        pass
            except Exception:
                pass
            continue
        else:
            logger.info(f"[Layer5] CF challenge resolved after {(i+1)*3}s")
            return True
    return False


async def attempt(url: str) -> Optional[str]:
    """Bypass using headed Playwright browser (Xvfb)."""
    logger.info(f"[Layer5] Starting headed Playwright for: {url[:80]}")

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.warning("[Layer5] Playwright not installed")
        return None

    original_domain = urlparse(url).netloc.lower().replace('www.', '')
    browser = None
    pw = None

    try:
        pw = await async_playwright().start()

        # Use headed mode - Xvfb provides the display
        # Headed mode is much harder for CF to detect than headless
        browser = await pw.chromium.launch(
            headless=False,
            args=[
                '--no-sandbox', '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-site-isolation-trials',
                '--window-size=1920,1080',
            ]
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

        # Track navigation destinations via response interception
        destinations = []

        def on_response(response):
            try:
                resp_url = response.url
                if response.status in (301, 302, 307, 308):
                    loc = response.headers.get('location', '')
                    if _is_dest(loc, original_domain):
                        destinations.append(loc)
                if _is_dest(resp_url, original_domain):
                    destinations.append(resp_url)
            except Exception:
                pass

        page.on('response', on_response)

        try:
            # Navigate with longer timeout for CF
            response = await page.goto(url, wait_until='domcontentloaded', timeout=45000)
            logger.info(f"[Layer5] Initial load: {response.status if response else 'no response'}, url: {page.url[:80]}")

            # Check if we already landed on destination
            if _is_dest(page.url, original_domain):
                return page.url

            # Wait for CF challenge to resolve
            content = await page.content()
            title = await page.title()
            if 'Just a moment' in title or 'challenge-platform' in content:
                logger.info("[Layer5] CF challenge detected, waiting...")
                cf_ok = await _wait_for_cf(page, timeout_sec=45)
                if not cf_ok:
                    logger.warning("[Layer5] CF challenge did not resolve in time")
                    # Still continue - maybe partial load works

            # Check destination again after CF
            if _is_dest(page.url, original_domain):
                return page.url

            # Now we should be on the actual shortener page (AdLinkFly etc)
            await page.wait_for_timeout(2000)
            content = await page.content()
            logger.info(f"[Layer5] Post-CF page title: {await page.title()}, url: {page.url[:80]}")

            # Look for countdown timer
            timer_match = re.search(r'var\s+(?:count|timer|countdown|seconds|wait|time)\s*=\s*(\d+)', content)
            if timer_match:
                wait_sec = min(int(timer_match.group(1)), 25)
                logger.info(f"[Layer5] Found timer: {wait_sec}s, waiting...")
                await page.wait_for_timeout(wait_sec * 1000 + 3000)
            else:
                # Default wait for potential hidden timers
                await page.wait_for_timeout(8000)

            # Check destination after timer
            if _is_dest(page.url, original_domain):
                return page.url

            # Try clicking bypass/continue buttons
            button_selectors = [
                '#btn-main', '#continue', '#bypass', '#get-link',
                '.get-link', '#link-button', '.link-button',
                'a.btn-primary', 'a.btn-success',
                'button.btn-primary', 'button.btn-success',
                '[id*="continue"]', '[id*="bypass"]', '[id*="getlink"]',
                '[class*="continue"]', '[class*="bypass"]', '[class*="getlink"]',
                'a[href*="go"]', 'a[href*="redirect"]',
                'input[type="submit"]', 'button[type="submit"]',
                '.btn-main', '#btn-go', '.btn-go',
                '#surl', '#skip', '.skip-btn',
                'a.btn[href]', '#go-link', '.go-link',
            ]

            for selector in button_selectors:
                try:
                    els = await page.query_selector_all(selector)
                    for el in els:
                        if await el.is_visible():
                            logger.info(f"[Layer5] Clicking button: {selector}")
                            await el.click()
                            await page.wait_for_timeout(4000)
                            new_url = page.url
                            if _is_dest(new_url, original_domain):
                                logger.info(f"[Layer5] Got destination via button click: {new_url[:80]}")
                                return new_url
                except Exception:
                    continue

            # Extract from page content
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
                        logger.info(f"[Layer5] Found destination in HTML: {m.group(1)[:80]}")
                        return m.group(1)

            # Check network interception results
            if destinations:
                logger.info(f"[Layer5] Got destination from network: {destinations[-1][:80]}")
                return destinations[-1]

            # Final retry loop - wait more and check
            for attempt_num in range(3):
                await page.wait_for_timeout(5000)
                if _is_dest(page.url, original_domain):
                    return page.url
                if destinations:
                    return destinations[-1]

                # Try buttons again
                for selector in button_selectors[:10]:
                    try:
                        el = await page.query_selector(selector)
                        if el and await el.is_visible():
                            await el.click()
                            await page.wait_for_timeout(3000)
                            if _is_dest(page.url, original_domain):
                                return page.url
                    except Exception:
                        continue

            logger.warning(f"[Layer5] Failed to find destination for {url[:60]}")

        except Exception as e:
            logger.warning(f"[Layer5] Navigation error: {type(e).__name__}: {e}")

    except Exception as e:
        logger.error(f"[Layer5] Setup error: {type(e).__name__}: {e}")
    finally:
        try:
            if browser:
                await browser.close()
            if pw:
                await pw.stop()
        except Exception:
            pass

    return None

"""
LinkBypass Pro — Layer 5: Stealth Playwright Browser v4.0
==========================================================
Real Chromium browser with comprehensive anti-detection:
- Playwright stealth patches (webdriver, plugins, languages, etc.)
- CF managed challenge auto-wait & auto-solve
- AdLinkFly flow automation (wait for timer, click buttons)
- Network interception for destination URL detection
- Intelligent content extraction from loaded page
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


async def attempt(url: str) -> Optional[str]:
    """Bypass using stealth Playwright browser."""
    logger.info(f"[Layer5] Starting stealth Playwright for: {url[:80]}")

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
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox', '--disable-setuid-sandbox',
                '--disable-dev-shm-usage', '--disable-gpu',
                '--single-process',
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
            response = await page.goto(url, wait_until='domcontentloaded', timeout=30000)

            for i in range(6):
                await page.wait_for_timeout(2500)
                current = page.url
                if _is_dest(current, original_domain):
                    logger.info(f"[Layer5] CF resolved -> {current}")
                    return current

                content = await page.content()
                if 'cf-browser-verification' not in content and 'challenge-platform' not in content:
                    break

            current = page.url
            if _is_dest(current, original_domain):
                return current

            content = await page.content()

            timer_match = re.search(r'var\s+(?:count|timer|countdown|seconds|wait)\s*=\s*(\d+)', content)
            if timer_match:
                wait_sec = min(int(timer_match.group(1)), 20)
                logger.info(f"[Layer5] Waiting {wait_sec}s for timer...")
                await page.wait_for_timeout(wait_sec * 1000 + 2000)

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
            ]

            for selector in button_selectors:
                try:
                    els = await page.query_selector_all(selector)
                    for el in els:
                        if await el.is_visible():
                            await el.click()
                            await page.wait_for_timeout(3000)
                            new_url = page.url
                            if _is_dest(new_url, original_domain):
                                return new_url
                except Exception:
                    continue

            content = await page.content()
            patterns = [
                r'window\.location(?:\.href)?\s*=\s*["\'](https?://[^"\' ]+)["\']',
                r'location\.replace\(["\'](https?://[^"\' ]+)["\']',
                r'"(?:url|link|destination|redirect)"\s*:\s*"(https?://[^"]+)"',
                r'var\s+(?:url|link|dest|redirect)\s*=\s*["\'](https?://[^"\' ]+)["\']',
                r'data-(?:url|href)\s*=\s*["\'](https?://[^"\'\s]+)["\']',
                r'<a[^>]+href=["\'](https?://[^"\'\s]+)["\'][^>]*(?:class|id)=["\'"][^"\']*(?:btn|button|continue|go|visit|download)',
            ]

            for pat in patterns:
                for m in re.finditer(pat, content, re.IGNORECASE):
                    if _is_dest(m.group(1), original_domain):
                        return m.group(1)

            if destinations:
                return destinations[-1]

            for _ in range(4):
                await page.wait_for_timeout(5000)
                current = page.url
                if _is_dest(current, original_domain):
                    return current

                for selector in button_selectors[:8]:
                    try:
                        el = await page.query_selector(selector)
                        if el and await el.is_visible():
                            await el.click()
                            await page.wait_for_timeout(2000)
                            if _is_dest(page.url, original_domain):
                                return page.url
                    except Exception:
                        continue

                if destinations:
                    return destinations[-1]

        except Exception as e:
            logger.warning(f"[Layer5] Nav error: {e}")

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

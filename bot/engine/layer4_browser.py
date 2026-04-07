"""
LinkBypass Pro — Layer 4: Playwright Browser Bypass
=====================================================
Uses Playwright (real Chromium) to bypass Cloudflare and JS challenges.
This is the most reliable bypass method for CF-protected shorteners.
"""

import asyncio
import logging
import random
import re
from typing import Optional
from urllib.parse import urlparse

from bot.config import USER_AGENTS
from bot.engine.url_utils import is_valid_url, get_domain, is_destination_url

logger = logging.getLogger(__name__)

# Playwright browser singleton
_browser = None
_browser_lock = asyncio.Lock()


async def _get_browser():
    """Get or create a Playwright browser instance (singleton)."""
    global _browser
    async with _browser_lock:
        if _browser is None or not _browser.is_connected():
            try:
                from playwright.async_api import async_playwright
                pw = await async_playwright().start()
                _browser = await pw.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--disable-extensions',
                        '--disable-background-networking',
                        '--disable-default-apps',
                        '--disable-sync',
                        '--no-first-run',
                        '--single-process',
                        '--disable-blink-features=AutomationControlled',
                    ]
                )
                logger.info("[Layer4] Playwright browser launched")
            except Exception as e:
                logger.error(f"[Layer4] Failed to launch browser: {e}")
                return None
        return _browser


async def attempt(url: str) -> Optional[str]:
    """
    Bypass a URL using Playwright headless browser.
    Navigates to the URL, waits for CF/JS challenges to resolve,
    handles timers/countdowns, and captures the final destination URL.
    """
    logger.info(f"[Layer4] Playwright bypass for: {url[:80]}")
    original_domain = get_domain(url)
    browser = await _get_browser()
    if not browser:
        logger.warning("[Layer4] No browser available")
        return None

    context = None
    page = None
    try:
        context = await browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={'width': 1366, 'height': 768},
            locale='en-US',
            timezone_id='America/New_York',
            java_script_enabled=True,
            bypass_csp=True,
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
                'DNT': '1',
            }
        )

        # Stealth patches
        await context.add_init_script("""
            // Override navigator properties to avoid detection
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            window.chrome = {runtime: {}};
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({state: Notification.permission}) :
                originalQuery(parameters)
            );
        """)

        page = await context.new_page()
        
        # Track navigation - capture all URLs we pass through
        visited_urls = []
        final_url = [url]
        
        def on_response(response):
            resp_url = response.url
            if response.status in (301, 302, 303, 307, 308):
                loc = response.headers.get('location', '')
                if loc:
                    visited_urls.append(loc)
        
        page.on('response', on_response)

        # Navigate with extended timeout for CF challenges
        try:
            response = await page.goto(url, wait_until='domcontentloaded', timeout=45000)
        except Exception as e:
            logger.warning(f"[Layer4] Navigation timeout/error: {e}")
            # Even on timeout, check if we redirected
            current = page.url
            if get_domain(current) != original_domain and is_destination_url(current, original_domain):
                return current
            return None

        # Wait for any CF challenge to complete (check for redirects)
        await asyncio.sleep(2)
        current_url = page.url
        
        # If already redirected to a different domain, we're done
        if get_domain(current_url) != original_domain and is_destination_url(current_url, original_domain):
            logger.info(f"[Layer4] Direct redirect to: {current_url}")
            return current_url

        # Wait for page to fully load after CF
        try:
            await page.wait_for_load_state('networkidle', timeout=15000)
        except:
            pass

        current_url = page.url
        if get_domain(current_url) != original_domain and is_destination_url(current_url, original_domain):
            return current_url

        # ---- Handle AdLinkFly-type pages with timers ----
        page_content = await page.content()
        
        # Look for countdown timers and wait
        countdown_match = re.search(r'(?:var\s+(?:count|timer|seconds|wait|time)\s*=\s*(\d+))', page_content)
        wait_time = 8  # default
        if countdown_match:
            wait_time = min(int(countdown_match.group(1)), 15)
        
        # Check if there's a "get link" / "go" / "continue" / "click here" button
        # Wait for timer first
        await asyncio.sleep(wait_time)
        
        # Try clicking common bypass buttons
        button_selectors = [
            '#btn-main',           # AdLinkFly standard
            '.get-link',           # Common class
            '#getLink',            # Common ID
            'a.btn-success',       # Bootstrap green button
            '#go-link',
            '.go-link',
            'a[href*="go"]',
            '#continue',
            '.continue-btn',
            'a.btn[href]',
            '#download-link',
            '.download-btn',
            'button[type="submit"]',
            '#verify_button',
            '#verify_btn',
            '#wpsafe-link a',
            '.wpsafe-bottom a',
            '#surl a',
            'a.btn-primary',
        ]
        
        for selector in button_selectors:
            try:
                elem = await page.query_selector(selector)
                if elem and await elem.is_visible():
                    # Check if button has a direct href
                    href = await elem.get_attribute('href')
                    if href and href.startswith('http') and get_domain(href) != original_domain:
                        logger.info(f"[Layer4] Found link in button href: {href}")
                        return href
                    
                    # Click the button
                    await elem.click()
                    await asyncio.sleep(3)
                    
                    current_url = page.url
                    if get_domain(current_url) != original_domain and is_destination_url(current_url, original_domain):
                        logger.info(f"[Layer4] After click redirect to: {current_url}")
                        return current_url
            except Exception:
                continue

        # Try extracting URLs from page content after all interactions
        page_content = await page.content()
        
        # Look for destination URLs in common patterns
        dest_patterns = [
            r'(?:var|let|const)\s+(?:url|link|dest|redirect|target)\s*=\s*["\'](https?://[^"\'>]+)',
            r'window\.(?:location|open)\s*[=(]\s*["\'](https?://[^"\'>]+)',
            r'href\s*=\s*["\'](https?://(?!(?:' + re.escape(original_domain) + r'))[^"\'>]+)',
            r'<a[^>]+id=["\']*(?:real|download|dest|final|target)[^>]*href=["\'](https?://[^"\'>]+)',
            r'data-(?:url|href|link)=["\'](https?://[^"\'>]+)',
        ]
        
        for pattern in dest_patterns:
            matches = re.findall(pattern, page_content, re.I)
            for match in matches:
                if is_valid_url(match) and get_domain(match) != original_domain:
                    if is_destination_url(match, original_domain):
                        logger.info(f"[Layer4] Found URL in content: {match}")
                        return match

        # Final check on current URL
        current_url = page.url
        if get_domain(current_url) != original_domain:
            return current_url

        # Check visited URLs from redirects
        for visited in reversed(visited_urls):
            if is_valid_url(visited) and get_domain(visited) != original_domain:
                if is_destination_url(visited, original_domain):
                    return visited

        logger.info("[Layer4] No destination found")
        return None

    except Exception as e:
        logger.error(f"[Layer4] Error: {e}")
        return None
    finally:
        try:
            if page:
                await page.close()
            if context:
                await context.close()
        except:
            pass


async def cleanup():
    """Close the browser on shutdown."""
    global _browser
    if _browser:
        try:
            await _browser.close()
        except:
            pass
        _browser = None

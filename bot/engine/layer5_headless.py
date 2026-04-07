"""
LinkBypass Pro — Layer 5: Playwright Headless Browser
======================================================
Uses a real Chromium browser via Playwright to bypass
Cloudflare-protected shorteners. This is the most reliable
but slowest method.
"""

import re
import logging
import asyncio
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


async def attempt(url: str) -> Optional[str]:
    """Bypass using Playwright headless browser."""
    logger.info(f"[Layer5] Starting Playwright bypass for: {url[:80]}")
    
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.warning("[Layer5] Playwright not installed")
        return None

    original_domain = urlparse(url).netloc
    browser = None
    
    try:
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox', 
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--single-process',
                '--disable-blink-features=AutomationControlled',
            ]
        )
        
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            java_script_enabled=True,
        )
        
        # Anti-detection
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            window.chrome = {runtime: {}};
        """)
        
        page = await context.new_page()
        
        # Track navigation
        final_url = [url]
        
        def on_response(response):
            resp_url = response.url
            resp_domain = urlparse(resp_url).netloc
            if resp_domain != original_domain and not any(x in resp_domain for x in [
                'google', 'facebook', 'cloudflare', 'gstatic', 'jsdelivr', 
                'jquery', 'bootstrap', 'cdn', 'analytics', 'doubleclick',
                'adsense', 'adservice', 'tracking'
            ]):
                final_url[0] = resp_url
        
        page.on('response', on_response)
        
        try:
            # Navigate with generous timeout for CF challenge
            response = await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            # Wait for potential CF challenge to resolve
            await page.wait_for_timeout(3000)
            
            # Check if page URL changed
            current = page.url
            current_domain = urlparse(current).netloc
            if current_domain != original_domain and current_domain:
                logger.info(f"[Layer5] Navigated to: {current}")
                await browser.close()
                await pw.stop()
                return current
            
            # Wait for page to fully load
            await page.wait_for_timeout(5000)
            
            # Try to find and click continue/bypass buttons
            button_selectors = [
                'a.btn-primary', 'a.btn-success', 'a.btn',
                'button.btn-primary', 'button.btn-success',
                '#btn-main', '#continue', '#bypass',
                'a[href*="go"], a[href*="redirect"]',
                '.link-button', '#link-button',
                'a.get-link', '#get-link',
                '[id*="continue"]', '[id*="bypass"]', '[id*="download"]',
                '[class*="continue"]', '[class*="bypass"]', '[class*="download"]',
                'input[type="submit"]', 'button[type="submit"]',
            ]
            
            for selector in button_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for el in elements:
                        if await el.is_visible():
                            await el.click()
                            await page.wait_for_timeout(3000)
                            
                            new_url = page.url
                            new_domain = urlparse(new_url).netloc
                            if new_domain != original_domain and new_domain:
                                logger.info(f"[Layer5] Button click led to: {new_url}")
                                await browser.close()
                                await pw.stop()
                                return new_url
                except Exception:
                    continue
            
            # Try extracting destination from page content
            content = await page.content()
            
            # Look for destination URLs in the page
            patterns = [
                r'window\.location(?:\.href)?\s*=\s*["\'](https?://[^"\'\']+)["\'\']',
                r'<a[^>]+href=["\'](https?://[^"\'\'\s]+)["\'\'][^>]*(?:class|id)=["\'\'][^"\'\']*(?:btn|button|continue|redirect|go|visit|download)',
                r'"(?:url|link|destination|redirect)"\s*:\s*"(https?://[^"]+)"',
                r'var\s+(?:url|link|dest|redirect)\s*=\s*["\'](https?://[^"\'\']+)["\'\']',
                r'data-(?:url|href)=["\'](https?://[^"\'\'\s]+)["\'\']',
            ]
            
            for pat in patterns:
                matches = re.findall(pat, content, re.IGNORECASE)
                for match in matches:
                    match_domain = urlparse(match).netloc
                    if match_domain and match_domain != original_domain:
                        if not any(x in match_domain for x in ['google', 'facebook', 'cloudflare', 'gstatic', 'cdn']):
                            logger.info(f"[Layer5] Extracted from content: {match[:80]}")
                            await browser.close()
                            await pw.stop()
                            return match
            
            # Wait longer and check for delayed redirects
            for _ in range(6):  # Wait up to 30 more seconds
                await page.wait_for_timeout(5000)
                current = page.url
                current_domain = urlparse(current).netloc
                if current_domain != original_domain and current_domain:
                    logger.info(f"[Layer5] Delayed redirect to: {current}")
                    await browser.close()
                    await pw.stop()
                    return current
                
                # Try clicking any new buttons that appeared
                for selector in button_selectors[:5]:
                    try:
                        el = await page.query_selector(selector)
                        if el and await el.is_visible():
                            await el.click()
                            await page.wait_for_timeout(2000)
                            new_url = page.url
                            if urlparse(new_url).netloc != original_domain:
                                await browser.close()
                                await pw.stop()
                                return new_url
                    except Exception:
                        continue
        
        except Exception as e:
            logger.warning(f"[Layer5] Navigation error: {e}")
        
        await browser.close()
        await pw.stop()
        
    except Exception as e:
        logger.error(f"[Layer5] Playwright error: {type(e).__name__}: {e}")
        if browser:
            try:
                await browser.close()
            except Exception:
                pass
    
    return None

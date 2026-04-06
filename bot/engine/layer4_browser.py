import httpx
import re

async def attempt(url):
    """Headless-like approach using cloudscraper"""
    try:
        import cloudscraper
        scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
        resp = scraper.get(url, allow_redirects=True, timeout=20)
        final = resp.url

        if final != url:
            return {"success": True, "url": final, "method": "cloudscraper"}

        t = resp.text
        patterns = [
            r'var\s+url\s*=\s*["\'](https?://[^"\']+)["\']',
            r'href=["\']([^"\']*(?:mega|drive\.google|mediafire|dropbox)[^"\']*)["\']',
            r'window\.open\(["\']([^"\']+)["\']',
        ]
        for pat in patterns:
            m = re.search(pat, t)
            if m:
                return {"success": True, "url": m.group(1), "method": "cloudscraper_js"}

        return {"success": False, "url": None, "method": None}
    except Exception:
        return {"success": False, "url": None, "method": None}

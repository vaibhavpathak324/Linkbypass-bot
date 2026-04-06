import re
import logging

logger = logging.getLogger(__name__)

async def attempt(url):
    """Cloudscraper-like approach. Returns URL string or None."""
    try:
        import cloudscraper
        scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
        resp = scraper.get(url, allow_redirects=True, timeout=20)
        final = str(resp.url)

        if final != url:
            logger.info(f"[Layer4] Cloudscraper redirect: {final}")
            return final

        t = resp.text
        patterns = [
            r'var\s+url\s*=\s*["\'](https?://[^"\']+)["\']',
            r'href=["\']([^"\']*(?:mega|drive\.google|mediafire|dropbox)[^"\']*)["\']',
            r'window\.open\(["\']([^"\']+)["\']',
        ]
        for pat in patterns:
            m = re.search(pat, t)
            if m:
                found = m.group(1)
                if found.startswith('http') and found != url:
                    return found

        return None
    except ImportError:
        logger.warning("[Layer4] cloudscraper not installed, skipping")
        return None
    except Exception as e:
        logger.debug(f"[Layer4] Error: {e}")
        return None

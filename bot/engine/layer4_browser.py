import re

async def attempt(url):
    try:
        import cloudscraper
        scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
        resp = scraper.get(url, allow_redirects=True, timeout=20)
        final = resp.url
        if str(final) != url:
            return str(final)
        text = resp.text
        patterns = [
            r'var\s+url\s*=\s*["\'](https?://[^"\'\']+)["\'\']',
            r'href=["\'\']([^"\'\']*(?:mega|drive\.google|mediafire|dropbox)[^"\'\']*)["\'\']',
            r'window\.open\(["\'\']([^"\'\']+)["\'\']',
        ]
        for p in patterns:
            match = re.search(p, text)
            if match:
                found = match.group(1)
                if found.startswith("http") and found != url:
                    return found
    except:
        pass
    return None

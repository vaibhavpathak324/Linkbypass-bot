import httpx
import re
from urllib.parse import urlparse

async def attempt(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        async with httpx.AsyncClient(follow_redirects=False, timeout=15.0, headers=headers, verify=False) as client:
            current = url
            visited = set()
            for _ in range(15):
                if current in visited:
                    break
                visited.add(current)
                resp = await client.get(current, follow_redirects=False)
                if resp.status_code in (301, 302, 303, 307, 308):
                    location = resp.headers.get("location", "")
                    if location:
                        if location.startswith("/"):
                            p = urlparse(current)
                            location = f"{p.scheme}://{p.netloc}{location}"
                        current = location
                        continue
                if "text/html" in resp.headers.get("content-type", ""):
                    text = resp.text
                    meta = re.search(r'<meta[^>]*http-equiv=["\']refresh["\'][^>]*content=["\'][\d;]*url=([^"\'>\s]+)', text, re.IGNORECASE)
                    if meta:
                        current = meta.group(1)
                        continue
                    for pattern in [
                        r'window\.location\.href\s*=\s*["\']([^"\']+)["\']',
                        r'window\.location\.replace\s*\(\s*["\']([^"\']+)["\']',
                        r'window\.location\s*=\s*["\']([^"\']+)["\']',
                    ]:
                        match = re.search(pattern, text)
                        if match:
                            loc = match.group(1)
                            if loc.startswith("/"):
                                p = urlparse(current)
                                loc = f"{p.scheme}://{p.netloc}{loc}"
                            current = loc
                            break
                    else:
                        break
                    continue
                break
            if current != url:
                return current
    except Exception:
        pass
    return None

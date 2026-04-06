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
        async with httpx.AsyncClient(
            follow_redirects=True,
            max_redirects=15,
            timeout=15.0,
            headers=headers,
        ) as client:
            resp = await client.get(url)

            final_url = str(resp.url)
            original_domain = urlparse(url).netloc
            final_domain = urlparse(final_url).netloc

            if final_domain != original_domain and final_url != url:
                return {"success": True, "url": final_url, "method": "redirect_follow"}

            # Check for meta refresh or JS redirect in HTML
            if resp.status_code == 200:
                text = resp.text[:10000]

                # Meta refresh
                meta = re.search(r'<meta[^>]*http-equiv=["\']refresh["\'][^>]*content=["\'][^;]*;url=([^"\']+)["\']', text, re.I)
                if meta:
                    return {"success": True, "url": meta.group(1).strip(), "method": "meta_refresh"}

                # JS redirect patterns
                js_patterns = [
                    r'window\.location\.href\s*=\s*["\']([^"\']+)["\']',
                    r'window\.location\.replace\s*\(\s*["\']([^"\']+)["\']',
                    r'window\.location\s*=\s*["\']([^"\']+)["\']',
                ]
                for pat in js_patterns:
                    m = re.search(pat, text)
                    if m:
                        found_url = m.group(1)
                        if found_url.startswith('http') and found_url != url:
                            return {"success": True, "url": found_url, "method": "js_redirect"}

        return {"success": False, "url": None, "method": None}
    except Exception:
        return {"success": False, "url": None, "method": None}

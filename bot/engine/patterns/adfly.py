import httpx
import re
import base64

DOMAINS = ["adf.ly","j.gs","q.gs","ay.gy","atominik.com","tinyium.com","microify.com","pintient.com","babfrm.com"]

async def bypass(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        async with httpx.AsyncClient(follow_redirects=False, timeout=15.0, headers=headers) as client:
            resp = await client.get(url)
            text = resp.text

            # Method 1: Look for var url in script
            match = re.search(r'var\s+yab\s*=\s*["\']([A-Za-z0-9+/=]+)["\']', text)
            if match:
                try:
                    decoded = base64.b64decode(match.group(1)).decode('utf-8')
                    if decoded.startswith('http'):
                        return decoded
                except:
                    pass

            # Method 2: Look for var url = "https:..."
            match2 = re.search(r'var url\s*=\s*["\'](https?://[^"\']+)["\']', text)
            if match2:
                return match2.group(1)

            # Method 3: Check location header
            if resp.status_code in (301, 302, 303, 307, 308):
                loc = resp.headers.get('location', '')
                if loc and loc != url:
                    return loc

            # Method 4: Decode all base64 strings
            for m in re.finditer(r'["\']([A-Za-z0-9+/=]{20,})["\']', text):
                try:
                    d = base64.b64decode(m.group(1)).decode('utf-8')
                    if d.startswith('http'):
                        return d
                except:
                    continue

        return None
    except Exception:
        return None

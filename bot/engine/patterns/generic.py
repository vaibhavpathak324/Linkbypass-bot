import httpx
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import base64

DOMAINS = []  # Fallback - no specific domains

async def bypass(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
        }
        async with httpx.AsyncClient(follow_redirects=True, timeout=20.0, headers=headers) as client:
            resp = await client.get(url)
            t = resp.text
            soup = BeautifulSoup(t, 'html.parser')

            # Method 1: Meta refresh
            meta = soup.find('meta', attrs={'http-equiv': re.compile('refresh', re.I)})
            if meta:
                content = meta.get('content', '')
                m = re.search(r'url=([^\s"\']+)', content, re.I)
                if m:
                    return m.group(1).strip('"\'')

            # Method 2: Hidden form
            form = soup.find('form', {'method': re.compile('post', re.I)})
            if form:
                action = form.get('action', '')
                if not action.startswith('http'):
                    action = urljoin(url, action)
                data = {}
                for input_tag in form.find_all('input'):
                    n = input_tag.get('name')
                    v = input_tag.get('value', '')
                    if n:
                        data[n] = v
                resp2 = await client.post(action, data=data)
                final = str(resp2.url)
                if final != url:
                    return final

            # Method 3: Base64 decode
            for m in re.finditer(r'(?:atob|base64_decode)\s*\(\s*["\']([A-Za-z0-9+/=]{16,})["\']', t):
                try:
                    d = base64.b64decode(m.group(1)).decode('utf-8')
                    if d.startswith('http'):
                        return d
                except:
                    continue

            # Method 4: JS redirect patterns
            js_patterns = [
                r'(?:var|let|const)\s+(?:url|link|dest|destination|redirect|go|target)\s*=\s*["\'](https?://[^"\']+)["\']',
                r'window\.location(?:\.href)?\s*=\s*["\']([^"\']+)["\']',
                r'redirect\s*\(\s*["\']([^"\']+)["\']',
            ]
            for pat in js_patterns:
                match = re.search(pat, t)
                if match:
                    found = match.group(1)
                    if found.startswith('http') and found != url:
                        return found

            # Method 5: Final URL check
            final_url = str(resp.url)
            if final_url != url and urlparse(final_url).netloc != urlparse(url).netloc:
                return final_url

        return None
    except Exception:
        return None

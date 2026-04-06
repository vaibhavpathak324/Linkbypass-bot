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
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        async with httpx.AsyncClient(follow_redirects=True, timeout=20.0, headers=headers, verify=False) as client:
            resp = await client.get(url)
            final_url = str(resp.url)
            
            # If redirected to a different domain, that's the destination
            orig_domain = urlparse(url).netloc
            final_domain = urlparse(final_url).netloc
            if final_domain != orig_domain and final_url != url:
                return final_url
            
            text = resp.text
            soup = BeautifulSoup(text, "html.parser")
            
            # Look for destination URL patterns in the page
            # 1. Meta refresh
            meta = soup.find("meta", attrs={"http-equiv": re.compile("refresh", re.I)})
            if meta:
                content = meta.get("content", "")
                m = re.search(r'url=([^\s"\']+)', content, re.I)
                if m:
                    dest = m.group(1)
                    if not dest.startswith("http"):
                        dest = urljoin(final_url, dest)
                    return dest
            
            # 2. Look for "get link" / "continue" buttons
            for a in soup.find_all("a", href=True):
                txt = (a.get_text() or "").lower().strip()
                href = a["href"]
                if any(kw in txt for kw in ["get link", "continue", "go to", "click here", "download", "skip"]):
                    if href.startswith("http") and urlparse(href).netloc != orig_domain:
                        return href
            
            # 3. Base64 encoded URLs
            for m in re.finditer(r'(?:atob|base64_decode)\s*\(\s*["\']([A-Za-z0-9+/=]{16,})["\']', text):
                try:
                    decoded = base64.b64decode(m.group(1)).decode()
                    if decoded.startswith("http") and urlparse(decoded).netloc != orig_domain:
                        return decoded
                except:
                    pass
            
            # 4. URL in JavaScript variables
            for pattern in [
                r'(?:var|let|const)\s+(?:url|link|dest|destination|redirect|go|target)\s*=\s*["\']([^"\']+)["\']',
                r'window\.location(?:\.href)?\s*=\s*["\']([^"\']+)["\']',
                r'redirect\s*\(\s*["\']([^"\']+)["\']',
            ]:
                m = re.search(pattern, text)
                if m:
                    found = m.group(1)
                    if found.startswith("http") and urlparse(found).netloc != orig_domain:
                        return found
                        
    except Exception:
        pass
    return None

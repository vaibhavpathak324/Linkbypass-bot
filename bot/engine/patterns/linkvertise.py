import httpx
import re
import json
import base64

DOMAINS = [
    "linkvertise.com","link-target.net","link-center.net","link-hub.net",
    "direct-link.net","link-to.net","up-to-down.net","link-mutation.com",
]


async def bypass(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        async with httpx.AsyncClient(follow_redirects=True, timeout=20.0, headers=headers) as client:
            resp = await client.get(url)
            text = resp.text

            # Method 1: JSON data in page
            match = re.search(r'{\s*".+?"\s*:\s*".*?url.*?"\s*}', text)
            if match:
                try:
                    data = json.loads(match.group(0))
                    for k, v in data.items():
                        if isinstance(v, str) and v.startswith('http'):
                            dest = v.replace("\\/", "/")
                            return dest
                except:
                    pass

            for m in re.finditer(r'atob\(["\']([A-Za-z0-9+/=]{20,})["\']', text):
                try:
                    d = base64.b64decode(m.group(1)).decode('utf-8')
                    if d.startswith('http'):
                        return d
                except:
                    continue

            # Method 3: Check for API endpoint
            api_match = re.search(r'/api/v1/redirect/[^"\'\s]+', text)
            if api_match:
                api_url = "https://linkvertise.com" + api_match.group(0)
                resp2 = await client.get(api_url)
                try:
                    data = resp2.json()
                    if 'target' in data:
                        return data['target']
                except:
                    pass

            # Method 4: Final URL check
            final = str(resp.url)
            if final != url and 'linkvertise' not in final:
                return final

        return None
    except Exception:
        return None

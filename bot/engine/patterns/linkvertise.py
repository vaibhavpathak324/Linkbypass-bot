import httpx, re, base64

DOMAINS = ["linkvertise.com","link-target.net","link-center.net","link-hub.net","direct-link.net","link-to.net","up-to-down.net","link-mutation.com"]

async def bypass(url):
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(f"https://api.bypass.vip/bypass?url={url}")
            if resp.status_code == 200:
                data = resp.json()
                dest = data.get("destination") or data.get("result")
                if dest and dest != url:
                    return dest
    except:
        pass
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Accept": "text/html"}
        async with httpx.AsyncClient(follow_redirects=True, timeout=20.0, headers=headers) as client:
            resp = await client.get(url)
            text = resp.text
            match = re.search(r'"destination"\s*:\s*"([^"]+)"', text)
            if match:
                dest = match.group(1).replace("\\/", "/")
                if dest.startswith("http"):
                    return dest
            for m in re.finditer(r'atob\(["\'"]([A-Za-z0-9+/=]{20,})["\'"]', text):
                try:
                    decoded = base64.b64decode(m.group(1)).decode()
                    if decoded.startswith("http"):
                        return decoded
                except:
                    pass
    except:
        pass
    return None

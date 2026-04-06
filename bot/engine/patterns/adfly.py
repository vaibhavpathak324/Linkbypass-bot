import httpx, re, base64

DOMAINS = ["adf.ly","j.gs","q.gs","ay.gy","atominik.com","tinyium.com","microify.com","pintient.com","babfrm.com"]

async def bypass(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        async with httpx.AsyncClient(follow_redirects=False, timeout=15.0, headers=headers) as client:
            resp = await client.get(url)
            text = resp.text
            match = re.search(r"var ysmm = '([^']+)'", text)
            if match:
                encoded = match.group(1)
                codes = []
                for i in range(0, len(encoded), 2):
                    codes.append(int(encoded[i:i+2], 16))
                decoded = "".join(chr(c) for c in codes)
                try:
                    result = base64.b64decode(decoded).decode()
                    if result.startswith("http"):
                        return result
                except:
                    pass
            match2 = re.search(r'var url\s*=\s*["\'](https?://[^"\']+)["\'"]', text)
            if match2:
                return match2.group(1)
    except:
        pass
    return None

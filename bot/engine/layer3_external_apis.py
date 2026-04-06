import httpx

BYPASS_APIS = [
    {"name": "bypass.vip", "url": "https://api.bypass.vip/bypass?url={url}", "method": "GET"},
    {"name": "api.bypass.pm", "url": "https://api.bypass.pm/bypass?url={url}", "method": "GET"},
]

async def attempt(url):
    for api in BYPASS_APIS:
        try:
            target = api["url"].format(url=url)
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(target)
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        for key in ["destination", "result", "bypassed", "url", "dest"]:
                            if key in data and data[key] and data[key] != url:
                                return data[key]
                    except:
                        text = resp.text.strip()
                        if text.startswith("http") and text != url:
                            return text
        except:
            continue
    return None

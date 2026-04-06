import httpx
import logging

logger = logging.getLogger(__name__)

BYPASS_APIS = [
    {
        "name": "bypass.vip",
        "url": "https://api.bypass.vip/bypass?url={url}",
        "method": "GET",
        "result_keys": ["destination", "result", "bypassed", "url", "dest"],
    },
    {
        "name": "bypass.pm",
        "url": "https://api.bypass.pm/bypass?url={url}",
        "method": "GET",
        "result_keys": ["destination", "result", "bypassed", "url", "dest"],
    },
]

async def attempt(url):
    """Try multiple external bypass APIs."""
    for api in BYPASS_APIS:
        try:
            target = api["url"].format(url=url)
            logger.info(f"[Layer3] Trying {api['name']}")
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(target)
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        if isinstance(data, dict):
                            result_val = data.get("result", "")
                            if isinstance(result_val, str) and ("SHUT DOWN" in result_val.upper() or "discord" in result_val.lower()):
                                continue
                            for key in api.get("result_keys", []):
                                if key in data and data[key] and isinstance(data[key], str) and data[key].startswith("http") and data[key] != url:
                                    return data[key]
                    except Exception:
                        pass
                    text = resp.text.strip()
                    if text.startswith("http") and text != url and len(text) < 2000:
                        return text
        except Exception as e:
            logger.debug(f"[Layer3] {api['name']} error: {e}")
            continue
    return None

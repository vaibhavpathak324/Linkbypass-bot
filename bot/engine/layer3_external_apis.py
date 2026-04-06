import httpx
import logging

logger = logging.getLogger(__name__)

BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

async def _try_linkbypass_lol(url: str):
    """Primary bypass via linkbypass.lol API."""
    try:
        headers = {
            "Content-Type": "application/json",
            "xhamster": "010101010101010101010101010101010101010101010101101001",
            "User-Agent": BROWSER_UA,
            "Origin": "https://linkbypass.lol",
            "Referer": "https://linkbypass.lol/",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Ch-Ua": '"Chromium";v="131", "Not_A Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
        }
        payload = {"url": url, "ua": BROWSER_UA}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://linkbypass.lol/xhamster",
                headers=headers,
                json=payload,
            )
            if resp.status_code == 200:
                data = resp.json()
                logger.info(f"[linkbypass.lol] Response: {data}")
                if data.get("status") == "success":
                    result = data.get("url") or data.get("redirect") or data.get("result") or ""
                    if isinstance(result, str) and result.startswith("http") and result != url:
                        return result
                elif data.get("status") == "error":
                    msg = data.get("message", "")
                    logger.warning(f"[linkbypass.lol] Error: {msg}")
            else:
                logger.warning(f"[linkbypass.lol] HTTP {resp.status_code}")
    except Exception as e:
        logger.warning(f"[linkbypass.lol] Exception: {e}")
    return None


FALLBACK_APIS = [
    {
        "name": "bypass.vip",
        "url": "https://api.bypass.vip/bypass?url={url}",
        "method": "GET",
        "result_keys": ["destination", "result", "bypassed", "url", "dest"],
    },
    {
        "name": "fastt.dl",
        "url": "https://fastt-dl.vercel.app/api/bypass?url={url}",
        "method": "GET",
        "result_keys": ["destination", "result", "bypassed", "url", "dest"],
    },
]

async def _try_fallback_apis(url: str):
    """Try fallback bypass APIs."""
    for api in FALLBACK_APIS:
        try:
            target = api["url"].format(url=url)
            logger.info(f"[Layer3-fallback] Trying {api['name']}")
            async with httpx.AsyncClient(timeout=20.0, headers={"User-Agent": BROWSER_UA}) as client:
                if api["method"] == "POST":
                    resp = await client.post(target, json={"url": url})
                else:
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
            logger.debug(f"[Layer3-fallback] {api['name']} error: {e}")
            continue
    return None


async def attempt(url: str):
    """Try linkbypass.lol first, then fallback APIs."""
    result = await _try_linkbypass_lol(url)
    if result:
        return result
    result = await _try_fallback_apis(url)
    if result:
        return result
    return None

import logging
import httpx

logger = logging.getLogger(__name__)

DOMAINS = [
    "linkvertise.com", "link-to.net", "linkvertise.net"
]

async def bypass(url):
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get("https://bypass.pm/bypass2", params={"url": url})
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    return data.get("destination")
    except Exception as e:
        logger.warning(f"[Linkvertise] Error: {e}")
    return None

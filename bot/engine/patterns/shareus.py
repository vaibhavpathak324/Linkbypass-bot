import logging
import requests

logger = logging.getLogger(__name__)

DOMAINS = [
    "shareus.in", "shareus.io", "shrs.link"
]

async def bypass(url):
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _shareus_sync, url)
        return result
    except Exception as e:
        logger.warning(f"[ShareUs] Error: {e}")
        return None

def _shareus_sync(url):
    headers = {"user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"}
    DOMAIN = "https://us-central1-my-apps-server.cloudfunctions.net"
    sess = requests.session()
    code = url.split("/")[-1]
    params = {"shortid": code, "initial": "true", "referrer": "https://shareus.io/"}
    requests.get(f"{DOMAIN}/v", params=params, headers=headers, timeout=15)
    for i in range(1, 4):
        sess.post(f"{DOMAIN}/v", headers=headers, json={"current_page": i}, timeout=15)
    response = sess.get(f"{DOMAIN}/get_link", headers=headers, timeout=15).json()
    return response.get("link_info", {}).get("destination")

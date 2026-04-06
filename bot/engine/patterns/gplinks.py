import time
import re
import logging
import asyncio
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

DOMAINS = [
    "gplinks.com", "gplinks.in", "gplinks.co",
]

async def bypass(url):
    """GPLinks bypass using cloudscraper - follows the 3-step flow."""
    try:
        import cloudscraper
        from bs4 import BeautifulSoup
    except ImportError:
        logger.warning("[GPLinks] cloudscraper/bs4 not installed")
        return None

    try:
        client = cloudscraper.create_scraper(allow_brotli=False)
        p = urlparse(url)
        base = f"{p.scheme}://{p.netloc}"
        go_url = f"{base}/links/go"

        # Step 1: HEAD request to get redirect with postid
        resp = client.head(url, allow_redirects=False, timeout=15)
        header_loc = resp.headers.get("location", "")
        if not header_loc or "postid=" not in header_loc:
            resp = client.get(url, allow_redirects=False, timeout=15)
            header_loc = resp.headers.get("location", "")

        if not header_loc or "postid=" not in header_loc:
            logger.warning(f"[GPLinks] No redirect with postid found for {url}")
            return None

        param = header_loc.split("postid=")[-1]
        req_url = f"{base}/{param}"

        p2 = urlparse(header_loc)
        ref_url = f"{p2.scheme}://{p2.netloc}/"

        # Step 2: GET the form page
        h = {"referer": ref_url}
        resp2 = client.get(req_url, headers=h, allow_redirects=False, timeout=15)

        soup = BeautifulSoup(resp2.content, "html.parser")
        inputs = soup.find_all("input")
        data = {inp.get("name"): inp.get("value") for inp in inputs if inp.get("name")}

        if not data:
            logger.warning(f"[GPLinks] No form inputs found")
            return None

        # Step 3: Wait (required by GPLinks anti-bot) then POST
        logger.info(f"[GPLinks] Waiting 10s for timer...")
        await asyncio.sleep(10)

        h2 = {
            "content-type": "application/x-www-form-urlencoded",
            "x-requested-with": "XMLHttpRequest",
            "referer": req_url,
        }

        resp3 = client.post(go_url, headers=h2, data=data, timeout=15)

        try:
            result = resp3.json()
            dest = result.get("url", "")
            if dest and dest.startswith("http"):
                logger.info(f"[GPLinks] Bypassed: {dest}")
                return dest
        except Exception:
            m = re.search(r'"url"\s*:\s*"(https?://[^"]+)"', resp3.text)
            if m:
                return m.group(1)

        logger.warning(f"[GPLinks] POST response didn't contain URL: {resp3.text[:200]}")
        return None
    except Exception as e:
        logger.warning(f"[GPLinks] Error: {e}")
        return None

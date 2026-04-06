import re
import time
import logging
import asyncio
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

ADLINKFLY_SITES = {
    "gplinks.co": {"wait": 10, "referer": "https://mynewsmedia.co/"},
    "gplinks.com": {"wait": 10, "referer": "https://mynewsmedia.co/"},
    "gplinks.in": {"wait": 10, "referer": "https://mynewsmedia.co/"},
    "droplink.co": {"wait": 3.1},
    "droplinks.co": {"wait": 3.1},
    "rocklinks.net": {"wait": 10, "domain_override": "https://blog.disheye.com", "query": "?quelle="},
    "shortingly.in": {"wait": 5, "referer": "https://tech.gyanitheme.com/"},
    "shortingly.me": {"wait": 5, "referer": "https://tech.gyanitheme.com/"},
    "xpshort.com": {"wait": 8, "referer": "https://www.animalwallpapers.online/"},
    "push.bdnewsx.com": {"wait": 8, "referer": "https://www.animalwallpapers.online/"},
    "techymozo.com": {"wait": 8, "referer": "https://www.animalwallpapers.online/"},
    "short2url.in": {"wait": 10, "domain_override": "https://techyuth.xyz/blog", "referer": "https://blog.coin2pay.xyz/"},
    "try2link.com": {"wait": 7, "referer": "https://newforex.online/"},
    "try2links.com": {"wait": 7, "referer": "https://newforex.online/"},
    "gyanilinks.com": {"wait": 5, "domain_override": "https://go.hipsonyc.com"},
    "gtlinks.me": {"wait": 5, "domain_override": "https://go.hipsonyc.com"},
    "go.flashlink.in": {"wait": 15, "domain_override": "https://files.earnash.com", "referer": "https://flash1.cordtpoint.co.in"},
    "du-link.in": {"wait": 5},
    "ez4short.com": {"wait": 5},
    "krownlinks.me": {"wait": 5},
    "adrinolinks.com": {"wait": 5},
    "adrinolinks.in": {"wait": 5},
    "link.tnlink.in": {"wait": 5},
    "tnlink.in": {"wait": 5},
    "link.tnshort.net": {"wait": 5},
    "tnshort.net": {"wait": 5},
    "inshorturl.in": {"wait": 5},
    "inshorturl.com": {"wait": 5},
    "vplink.in": {"wait": 5},
    "arolinks.com": {"wait": 5},
    "linkshortify.com": {"wait": 5},
    "link1s.com": {"wait": 5},
    "earnlink.in": {"wait": 5},
    "za.gl": {"wait": 5},
    "short-url.link": {"wait": 5},
    "link4earn.com": {"wait": 5},
    "earn4link.in": {"wait": 5},
    "indianshortner.com": {"wait": 5},
    "atglinks.com": {"wait": 5},
    "rushload.com": {"wait": 5},
    "dropmb.com": {"wait": 5},
    "megafly.in": {"wait": 5},
    "usalink.io": {"wait": 5},
    "stfly.me": {"wait": 5},
    "stfly.xyz": {"wait": 5},
    "moneykamalo.com": {"wait": 5},
    "pglink.in": {"wait": 5},
    "shortzon.com": {"wait": 5},
    "tii.la": {"wait": 5},
    "shrinke.me": {"wait": 5},
    "urlshortx.com": {"wait": 5},
    "urlfly.me": {"wait": 5},
    "clicksfly.com": {"wait": 5},
    "clk.wiki": {"wait": 5},
    "onepagelink.com": {"wait": 5},
    "go.onepagelink.in": {"wait": 5},
    "quicr.co": {"wait": 5},
    "highcpmlink.com": {"wait": 5},
    "hitfly.net": {"wait": 5},
    "gyanilinks.in": {"wait": 5},
    "tekfly.me": {"wait": 5},
    "pkin.me": {"wait": 5},
    "modiurl.com": {"wait": 5},
    "owllink.net": {"wait": 5},
    "linksfly.link": {"wait": 5},
    "powerlinks.site": {"wait": 5},
    "modmakers.xyz": {"wait": 5},
    "modmakers.in": {"wait": 5},
    "linkpays.in": {"wait": 5},
    "mplaylink.com": {"wait": 5},
    "easysky.in": {"wait": 5},
    "indiurl.com": {"wait": 5},
    "giantlink.in": {"wait": 5},
    "indianlink.in": {"wait": 5},
    "publicearn.com": {"wait": 5},
    "go2url.in": {"wait": 5},
    "geturl.in": {"wait": 5},
    "cashurl.in": {"wait": 5},
    "earnow.online": {"wait": 5},
    "coinfly.in": {"wait": 5},
    "aylink.co": {"wait": 5},
    "adlinkfly.com": {"wait": 5},
    "adlinkfly.xyz": {"wait": 5},
    "adlinkfly.st": {"wait": 5},
    "go.indiurl.in.net": {"wait": 5},
    "linkbnao.com": {"wait": 5},
    "indianshortner.in": {"wait": 5},
    "mdiskshortners.in": {"wait": 5},
    "mdisky.link": {"wait": 5},
    "mdisklink.link": {"wait": 5},
    "rslinks.net": {"wait": 5},
    "kingurl.in": {"wait": 5},
    "link.vipurl.in": {"wait": 5},
    "vipurl.in": {"wait": 5},
    "shareus.in": {"wait": 5},
    "shareus.io": {"wait": 5},
}

DOMAINS = list(ADLINKFLY_SITES.keys())

_executor = ThreadPoolExecutor(max_workers=3)


def _gplinks_sync(url):
    import cloudscraper
    from bs4 import BeautifulSoup
    client = cloudscraper.create_scraper(allow_brotli=False)
    resp = client.get(url, allow_redirects=False, timeout=15)
    location = resp.headers.get("Location", "")
    if not location:
        return None
    vid = location.split("=")[-1]
    url_with_vid = f"{url}/?{vid}"
    resp2 = client.get(url_with_vid, allow_redirects=False, timeout=15)
    soup = BeautifulSoup(resp2.content, "html.parser")
    go_link = soup.find(id="go-link")
    if not go_link:
        return None
    inputs = go_link.find_all(name="input")
    data = {inp.get("name"): inp.get("value") for inp in inputs if inp.get("name")}
    time.sleep(10)
    headers = {"x-requested-with": "XMLHttpRequest"}
    p = urlparse(url)
    resp3 = client.post(f"{p.scheme}://{p.netloc}/links/go", data=data, headers=headers, timeout=15)
    try:
        return resp3.json()["url"]
    except Exception:
        return None


def _generic_adlinkfly_sync(url, config):
    import cloudscraper
    from bs4 import BeautifulSoup
    client = cloudscraper.create_scraper(allow_brotli=False)
    p = urlparse(url)
    domain_override = config.get("domain_override")
    DOMAIN = domain_override if domain_override else f"{p.scheme}://{p.netloc}"
    url_clean = url.rstrip("/")
    code = url_clean.split("/")[-1]
    query = config.get("query", "")
    final_url = f"{DOMAIN}/{code}{query}"
    headers = {}
    if config.get("referer"):
        headers["referer"] = config["referer"]
    resp = client.get(final_url, headers=headers, timeout=20)
    resp_domain = urlparse(str(resp.url)).netloc
    if resp_domain != p.netloc and resp_domain != urlparse(DOMAIN).netloc:
        return str(resp.url)
    soup = BeautifulSoup(resp.content, "html.parser")
    go_link = soup.find(id="go-link")
    if go_link:
        inputs = go_link.find_all(name="input")
    else:
        inputs = soup.find_all("input")
    data = {inp.get("name"): inp.get("value") for inp in inputs if inp.get("name")}
    if not data:
        form = soup.find("form")
        if form:
            action = form.get("action", "")
            if action:
                resp2 = client.get(action if action.startswith("http") else DOMAIN + action, timeout=15)
                soup2 = BeautifulSoup(resp2.content, "html.parser")
                inputs = soup2.find_all("input")
                data = {inp.get("name"): inp.get("value") for inp in inputs if inp.get("name")}
    if not data:
        return None
    wait_time = config.get("wait", 5)
    time.sleep(wait_time)
    post_headers = {"content-type": "application/x-www-form-urlencoded", "x-requested-with": "XMLHttpRequest"}
    go_endpoint = f"{DOMAIN}/links/go"
    resp3 = client.post(go_endpoint, data=data, headers=post_headers, timeout=15)
    try:
        result = resp3.json()
        dest = result.get("url", "")
        if dest and dest.startswith("http"):
            return dest
    except Exception:
        pass
    final = str(resp3.url)
    if urlparse(final).netloc != urlparse(DOMAIN).netloc:
        return final
    return None


def _try2link_sync(url):
    import cloudscraper
    from bs4 import BeautifulSoup
    client = cloudscraper.create_scraper(allow_brotli=False)
    url_clean = url.rstrip("/")
    params = (("d", int(time.time()) + (60 * 4)),)
    r = client.get(url_clean, params=params, headers={"Referer": "https://newforex.online/"}, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    go_link = soup.find(id="go-link")
    if not go_link:
        return None
    inputs = go_link.find_all(name="input")
    data = {inp.get("name"): inp.get("value") for inp in inputs if inp.get("name")}
    time.sleep(7)
    headers = {"Host": "try2link.com", "X-Requested-With": "XMLHttpRequest", "Origin": "https://try2link.com", "Referer": url_clean}
    resp = client.post("https://try2link.com/links/go", headers=headers, data=data, timeout=15)
    try:
        return resp.json()["url"]
    except Exception:
        return None


def _droplink_sync(url):
    import cloudscraper
    from bs4 import BeautifulSoup
    client = cloudscraper.create_scraper(allow_brotli=False)
    res = client.get(url, timeout=15)
    ref = re.findall(r"action\s*=\s*[\x27\"](.*?)[\x27\"]", res.text)
    if ref:
        h = {"referer": ref[0]}
        res = client.get(url, headers=h, timeout=15)
    soup = BeautifulSoup(res.content, "html.parser")
    inputs = soup.find_all("input")
    data = {inp.get("name"): inp.get("value") for inp in inputs if inp.get("name")}
    headers = {"content-type": "application/x-www-form-urlencoded", "x-requested-with": "XMLHttpRequest"}
    p = urlparse(url)
    final_url = f"{p.scheme}://{p.netloc}/links/go"
    time.sleep(3.1)
    resp = client.post(final_url, data=data, headers=headers, timeout=15)
    try:
        result = resp.json()
        return result.get("url")
    except Exception:
        return None


async def bypass(url):
    import asyncio
    loop = asyncio.get_event_loop()
    domain = urlparse(url).netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    config = ADLINKFLY_SITES.get(domain, {"wait": 5})
    try:
        if "gplinks" in domain:
            result = await loop.run_in_executor(_executor, _gplinks_sync, url)
        elif "try2link" in domain:
            result = await loop.run_in_executor(_executor, _try2link_sync, url)
        elif "droplink" in domain:
            result = await loop.run_in_executor(_executor, _droplink_sync, url)
        else:
            result = await loop.run_in_executor(_executor, _generic_adlinkfly_sync, url, config)
        if result and result.startswith("http"):
            logger.info(f"[AdLinkFly] Bypassed {domain}: {result}")
            return result
        return None
    except Exception as e:
        logger.warning(f"[AdLinkFly] Error for {domain}: {e}")
        return None

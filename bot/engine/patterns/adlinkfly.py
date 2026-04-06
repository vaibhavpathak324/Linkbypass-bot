import httpx
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

DOMAINS = [
    "vplink.in","arolinks.com","linkshortify.com","link1s.com","earnlink.in",
    "za.gl","short-url.link","link4earn.com","earn4link.in","indianshortner.com",
    "adrinolinks.com","techymozo.com","atglinks.com","rushload.com","short2url.in",
    "dropmb.com","ez4short.com","megafly.in","usalink.io","try2link.com",
    "try2links.com","stfly.me","stfly.xyz","shortingly.me","shortingly.in",
    "moneykamalo.com","pglink.in","shareus.in","shareus.io","shortzon.com",
    "tii.la","xpshort.com","shrinke.me","urlshortx.com","urlfly.me",
    "clicksfly.com","clk.wiki","tnlink.in","onepagelink.com","quicr.co",
    "highcpmlink.com","hitfly.net","gyanilinks.com","gyanilinks.in","tekfly.me",
    "pkin.me","modiurl.com","owllink.net","linksfly.link","powerlinks.site",
    "modmakers.xyz","modmakers.in","droplink.co","droplinks.co","rocklinks.net",
    "linkpays.in","dulink.in","mplaylink.com","tnshort.net","easysky.in",
    "indiurl.com","giantlink.in","indianlink.in","publicearn.com","go2url.in",
    "geturl.in","cashurl.in","earnow.online","quicklink.in","go-link.online",
    "bestcash2020.com","dulink.net","moneykamalo.in","linkpays.click",
    "wikitechgo.com","adlinkfly.xyz","shorturl.asia","illink.net",
    "cutsy.net","cutwin.com","123link.vip","tlink.in","tnvalue.in",
    "cutdl.xyz","shorterall.com","abcshort.com","adsafelink.com",
    "adlinkfly.com","adlinkfly.st","terabox.tech","megaurl.in",
]

async def bypass(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": url,
        }
        async with httpx.AsyncClient(follow_redirects=True, timeout=20.0, headers=headers, verify=False) as client:
            resp = await client.get(url)
            soup = BeautifulSoup(resp.text, "html.parser")

            form = soup.find("form", {"id": "link-view"}) or soup.find("form", {"method": "POST"})
            if form:
                action = form.get("action", "")
                if not action:
                    action = str(resp.url)
                elif not action.startswith("http"):
                    action = urljoin(str(resp.url), action)

                data = {}
                for inp in form.find_all("input"):
                    name = inp.get("name")
                    if name:
                        data[name] = inp.get("value", "")

                resp2 = await client.post(action, data=data, headers={**headers, "Referer": str(resp.url)})

                if str(resp2.url) != action and str(resp2.url) != url:
                    parsed = urlparse(str(resp2.url))
                    if parsed.netloc and parsed.netloc != urlparse(url).netloc:
                        return str(resp2.url)

                soup2 = BeautifulSoup(resp2.text, "html.parser")
                for a in soup2.find_all("a", href=True):
                    href = a["href"]
                    if href.startswith("http") and urlparse(href).netloc != urlparse(url).netloc:
                        if not any(x in href for x in ["javascript:", "#", "facebook.com", "twitter.com"]):
                            return href

            for script in soup.find_all("script"):
                text = script.string or ""
                b64_match = re.search(r\'atob\\(["\'\']([A-Za-z0-9+/=]+)["\'\']\\)\', text)
                if b64_match:
                    import base64
                    try:
                        decoded = base64.b64decode(b64_match.group(1)).decode()
                        if decoded.startswith("http"):
                            return decoded
                    except:
                        pass
                url_match = re.search(r\'(?:var\\s+(?:url|link|dest|destination|go)\\s*=\\s*["\'\'])(https?://[^\"\'\']+)\', text)
                if url_match:
                    found = url_match.group(1)
                    if urlparse(found).netloc != urlparse(url).netloc:
                        return found

            for a in soup.find_all("a", href=True):
                text_content = (a.get_text() or "").lower().strip()
                if any(w in text_content for w in ["get link", "go to link", "continue", "click here", "download"]):
                    href = a["href"]
                    if href.startswith("http") and urlparse(href).netloc != urlparse(url).netloc:
                        return href

    except Exception:
        pass
    return None

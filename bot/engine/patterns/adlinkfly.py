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
    "geturl.in","cashurl.in","earnow.online","coinfly.in","aylink.co",
    "adlinkfly.com","adlinkfly.xyz","adlinkfly.st",
]


async def bypass(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
        }
        async with httpx.AsyncClient(follow_redirects=True, timeout=20.0, headers=headers) as client:
            resp = await client.get(url)
            text = resp.text

            soup = BeautifulSoup(text, 'html.parser')

            # Method 1: Look for form with hidden inputs (common AdLinkFly pattern)
            form = soup.find('form', {'method': re.compile('post', re.I)})
            if form:
                action = form.get('action', '')
                if not action.startswith('http'):
                    parsed = urlparse(url)
                    action = urljoin(f"{parsed.scheme}://{parsed.netloc}", action)

                data = {}
                for input_tag in form.find_all('input'):
                    name = input_tag.get('name')
                    value = input_tag.get('value', '')
                    if name:
                        data[name] = value

                # Submit the form
                resp2 = await client.post(action, data=data)
                if resp2.is_redirect or resp2.has_redirect_location:
                    loc = resp2.headers.get('location', '')
                    if loc and loc != url:
                        return loc

                final2 = str(resp2.url)
                if final2 != url and not final2.endswith(urlparse(url).path):
                    return final2

                # Check response for destination URL
                text2 = resp2.text
                soup2 = BeautifulSoup(text2, 'html.parser')

                # Look for go link or destination link
                for a in soup2.find_all('a', href=True):
                    href = a.get('href', '')
                    if '/go/' in href or 'goto' in href or 'out' in href:
                        if href.startswith('http'):
                            return href

            # Method 2: Look for base64 encoded URL in JS
            import base64
            b64_match = re.search(r'atob\(["\']([A-Za-z0-9+/=]+)["\']\)', text)
            if b64_match:
                try:
                    decoded = base64.b64decode(b64_match.group(1)).decode('utf-8')
                    if decoded.startswith('http'):
                        return decoded
                except:
                    pass

            # Method 3: Look for var url = "..." pattern in JavaScript
            url_match = re.search(r'(?:var\s+(?:url|link|dest|destination|go)\s*=\s*["\'])(https?://[^"\']+)["\']', text)
            if url_match:
                return url_match.group(1)

            # Method 4: Check meta refresh
            meta = soup.find('meta', attrs={'http-equiv': re.compile('refresh', re.I)})
            if meta:
                content = meta.get('content', '')
                url_match = re.search(r'url=(.+)', content, re.I)
                if url_match:
                    return url_match.group(1).strip(' "\'')

            # Method 5: Follow any redirect countdown page
            final_url = str(resp.url)
            if final_url != url and urlparse(final_url).netloc != urlparse(url).netloc:
                return final_url

        return None
    except Exception:
        return None

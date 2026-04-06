import re
import base64
import logging
import asyncio
from urllib.parse import urlparse, urljoin

logger = logging.getLogger(__name__)

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
    "inshorturl.in","inshorturl.com",
]


async def bypass(url):
    """AdLinkFly bypass using cloudscraper to handle Cloudflare + multi-step forms."""
    try:
        import cloudscraper
        from bs4 import BeautifulSoup
    except ImportError:
        logger.warning("[AdLinkFly] cloudscraper/bs4 not installed")
        return None

    try:
        client = cloudscraper.create_scraper(
            allow_brotli=False,
            browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
        )
        p = urlparse(url)
        base = f"{p.scheme}://{p.netloc}"
        orig_domain = p.netloc

        # Step 1: GET the initial page (cloudscraper handles CF challenge)
        resp = client.get(url, timeout=20)
        text = resp.text

        # Check if we already got redirected to destination
        final_url = str(resp.url)
        final_domain = urlparse(final_url).netloc
        if final_domain != orig_domain and not _is_shortener_domain(final_domain):
            logger.info(f"[AdLinkFly] Direct redirect to: {final_url}")
            return final_url

        soup = BeautifulSoup(text, 'html.parser')

        # Method 1: Look for the "go" or "links/go" POST endpoint
        dest = await _try_adlinkfly_go(client, soup, text, url, base)
        if dest:
            return dest

        # Method 2: base64-encoded destination in JS
        dest = _try_base64_decode(text)
        if dest and dest != url:
            return dest

        # Method 3: Look for destination URL in page source
        dest = _try_regex_extraction(text, url)
        if dest:
            return dest

        # Method 4: Follow form submissions iteratively (multi-step)
        dest = await _try_form_chain(client, soup, text, url, base)
        if dest:
            return dest

        # Method 5: Check for /go/ or /out/ links
        for a in soup.find_all('a', href=True):
            href = a.get('href', '')
            if any(x in href for x in ['/go/', '/goto/', '/out/', '/redirect/']):
                full = href if href.startswith('http') else urljoin(base, href)
                resp2 = client.get(full, timeout=15, allow_redirects=True)
                final2 = str(resp2.url)
                if urlparse(final2).netloc != orig_domain:
                    return final2

        logger.warning(f"[AdLinkFly] All methods failed for {url}")
        return None
    except Exception as e:
        logger.warning(f"[AdLinkFly] Error: {e}")
        return None


async def _try_adlinkfly_go(client, soup, text, url, base):
    """Try the standard AdLinkFly /links/go POST method."""
    form = soup.find('form', {'method': re.compile('post', re.I)})
    if not form:
        form = soup.find('form', id=re.compile('link|go|bypass', re.I))
    if not form:
        return None

    action = form.get('action', '')
    if not action:
        action = f"{base}/links/go"
    elif not action.startswith('http'):
        action = urljoin(base, action)

    data = {}
    for inp in form.find_all('input'):
        name = inp.get('name')
        value = inp.get('value', '')
        if name:
            data[name] = value

    if not data:
        return None

    timer_match = re.search(r'(?:seconds?|timer|countdown)\s*[:=]\s*(\d+)', text, re.I)
    wait_time = int(timer_match.group(1)) if timer_match else 5
    wait_time = min(wait_time, 15)
    logger.info(f"[AdLinkFly] Waiting {wait_time}s for timer...")
    await asyncio.sleep(wait_time)

    headers = {
        "content-type": "application/x-www-form-urlencoded",
        "x-requested-with": "XMLHttpRequest",
        "referer": url,
    }

    try:
        resp = client.post(action, headers=headers, data=data, timeout=15)
        try:
            j = resp.json()
            dest = j.get("url") or j.get("destination") or j.get("link") or j.get("redirect")
            if dest and dest.startswith("http") and dest != url:
                return dest
        except Exception:
            pass

        final = str(resp.url)
        orig_domain = urlparse(url).netloc
        if urlparse(final).netloc != orig_domain:
            return final

        dest = _try_regex_extraction(resp.text, url)
        if dest:
            return dest
    except Exception as e:
        logger.debug(f"[AdLinkFly] Go POST failed: {e}")

    return None


async def _try_form_chain(client, soup, text, url, base):
    """Follow form submissions through multiple steps."""
    orig_domain = urlparse(url).netloc
    current_url = url
    current_text = text
    current_soup = soup

    for step in range(5):
        forms = current_soup.find_all('form')
        if not forms:
            break

        for form in forms:
            action = form.get('action', current_url)
            if not action.startswith('http'):
                action = urljoin(base, action)
            method = (form.get('method', 'get')).lower()

            data = {}
            for inp in form.find_all(['input', 'textarea']):
                name = inp.get('name')
                if name:
                    data[name] = inp.get('value', '')

            if not data:
                continue

            try:
                await asyncio.sleep(2)
                if method == 'post':
                    resp = client.post(action, data=data, timeout=15)
                else:
                    resp = client.get(action, params=data, timeout=15)

                final = str(resp.url)
                if urlparse(final).netloc != orig_domain and not _is_shortener_domain(urlparse(final).netloc):
                    return final

                current_text = resp.text
                current_soup = BeautifulSoup(current_text, 'html.parser')
                current_url = final

                dest = _try_regex_extraction(current_text, url)
                if dest:
                    return dest
            except Exception:
                continue

    return None


def _try_base64_decode(text):
    patterns = [
        r'atob\(["\']([ A-Za-z0-9+/=]+)["\'\])',
        r'decode\(["\']([ A-Za-z0-9+/=]+)["\'\])',
    ]
    for pat in patterns:
        for m in re.finditer(pat, text):
            try:
                decoded = base64.b64decode(m.group(1)).decode('utf-8')
                if decoded.startswith('http'):
                    return decoded
            except Exception:
                continue
    return None


def _try_regex_extraction(text, original_url):
    orig_domain = urlparse(original_url).netloc
    patterns = [
        r'(?:var\s+(?:url|link|dest|destination|go_url|final_url)\s*=\s*["\'\])(https?://[^"\']+)["\'\]',
        r'(?:window\.location(?:\.href)?\s*=\s*["\'\])(https?://[^"\']+)["\'\]',
        r'"url"\s*:\s*"(https?://[^"]+)"',
        r'"destination"\s*:\s*"(https?://[^"]+)"',
    ]
    for pat in patterns:
        for m in re.finditer(pat, text):
            found = m.group(1).replace('\\/', '/')
            if found.startswith('http') and urlparse(found).netloc != orig_domain:
                if not _is_shortener_domain(urlparse(found).netloc):
                    return found
    return None


def _is_shortener_domain(domain):
    shortener_indicators = [
        'inshorturl', 'gplinks', 'adlinkfly', 'shrinkme', 'shareus',
        'droplink', 'clicksfly', 'linkvertise', 'exe.io',
    ]
    return any(s in domain.lower() for s in shortener_indicators)

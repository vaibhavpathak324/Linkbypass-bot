"""
LinkBypass Pro — URL Utilities
===============================
Comprehensive URL parsing, validation, shortener detection,
and text processing utilities used throughout the bot.
"""

import re
import logging
from urllib.parse import urlparse, urljoin, parse_qs, unquote, quote
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# URL Validation & Parsing
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Comprehensive URL regex that handles most edge cases
URL_REGEX = re.compile(
    r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w\-._~:/?#\[\]@!$&\'()*+,;=%]*',
    re.IGNORECASE
)

# Strict URL regex for validation
STRICT_URL_REGEX = re.compile(
    r'^https?://'  # scheme
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,63}\.?|'  # domain
    r'localhost|'  # localhost
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ip
    r'(?::\d+)?'  # port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE
)


def is_valid_url(url: str) -> bool:
    """Check if a string is a valid HTTP/HTTPS URL."""
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    return bool(STRICT_URL_REGEX.match(url))


def extract_urls(text: str) -> List[str]:
    """Extract all URLs from a text string."""
    if not text:
        return []
    return URL_REGEX.findall(text)


def normalize_url(url: str) -> str:
    """Normalize a URL: ensure scheme, strip tracking params, etc."""
    url = url.strip()
    if not url:
        return url

    # Add scheme if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    # Parse and reconstruct
    parsed = urlparse(url)

    # Remove common tracking parameters
    tracking_params = {
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
        'fbclid', 'gclid', 'msclkid', 'twclid', 'igshid', 'ref', 'source',
    }

    if parsed.query:
        params = parse_qs(parsed.query, keep_blank_values=True)
        filtered = {k: v for k, v in params.items() if k.lower() not in tracking_params}
        if filtered:
            query = '&'.join(f"{k}={v[0]}" for k, v in filtered.items())
        else:
            query = ''
    else:
        query = ''

    # Reconstruct
    from urllib.parse import urlunparse
    result = urlunparse((
        parsed.scheme or 'https',
        parsed.netloc,
        parsed.path or '/',
        parsed.params,
        query,
        ''  # remove fragment
    ))

    return result


def get_domain(url: str) -> str:
    """Extract domain from URL, stripping www prefix."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        # Remove port
        if ':' in domain:
            domain = domain.split(':')[0]
        return domain
    except Exception:
        return ''


def get_base_url(url: str) -> str:
    """Get the base URL (scheme + domain) from a URL."""
    try:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        return url


def get_path(url: str) -> str:
    """Get the path portion of a URL."""
    try:
        return urlparse(url).path
    except Exception:
        return ''


def join_url(base: str, relative: str) -> str:
    """Join a base URL with a relative path."""
    return urljoin(base, relative)


def decode_url(url: str) -> str:
    """URL-decode a string."""
    return unquote(url)


def encode_url(url: str) -> str:
    """URL-encode a string (safe chars preserved)."""
    return quote(url, safe=':/?#[]@!$&\'()*+,;=')


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Shortener Detection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def detect_shortener(url: str) -> Tuple[str, str]:
    """
    Detect which shortener service a URL belongs to.
    Returns (shortener_name, category).
    Categories: adlinkfly, redirect, api_based, js_based, multi_step, unknown
    """
    domain = get_domain(url)
    if not domain:
        return ('unknown', 'unknown')

    # Import the domain list
    from bot.engine.domain_list import get_shortener_info
    info = get_shortener_info(domain)
    if info:
        return (info['name'], info.get('category', 'general'))

    # Check common patterns in URL structure
    path = get_path(url)

    # AdLinkFly pattern: domain.com/XXXX (short alphanumeric path)
    if re.match(r'^/[a-zA-Z0-9]{3,10}$', path):
        return (domain, 'possible_shortener')

    return ('unknown', 'unknown')


def is_shortener_url(url: str) -> bool:
    """Check if a URL is from a known shortener."""
    name, category = detect_shortener(url)
    return name != 'unknown'


def is_destination_url(url: str) -> bool:
    """
    Check if a URL looks like a final destination (not a shortener).
    Destination URLs typically are: direct download links, Google Drive,
    Mega.nz, MediaFire, etc.
    """
    domain = get_domain(url)
    destination_domains = {
        'drive.google.com', 'docs.google.com', 'mega.nz', 'mega.co.nz',
        'mediafire.com', 'dropbox.com', 'github.com', 'gitlab.com',
        'youtube.com', 'youtu.be', 'wikipedia.org', 'reddit.com',
        'stackoverflow.com', 'medium.com', 'notion.so', 'notion.site',
        'archive.org', 'web.archive.org', 'pastebin.com',
        'onedrive.live.com', 'sharepoint.com',
        'terabox.com', 'teraboxapp.com', '1024tera.com',
        'gofile.io', 'pixeldrain.com', 'krakenfiles.com',
        'uploadhaven.com', 'racaty.io', 'zippyshare.com',
        'solidfiles.com', 'userscloud.com', 'bayfiles.com',
        'anonfiles.com', 'file.io', 'send.cm',
        'hubcloud.lol', 'hubcloud.art', 'hubcloud.biz',
        'gdtot.pro', 'gdtot.cfd', 'new1.gdtot.sbs',
        'filepress.top', 'filepress.store',
        'androidatahost.com', 'androeed.ru',
        'apkmirror.com', 'apkpure.com',
    }
    return domain in destination_domains


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Text Utilities
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def truncate(text: str, max_len: int = 50) -> str:
    """Truncate a string with ellipsis."""
    if not text:
        return ''
    text = str(text)
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + '...'


def escape_md(text: str) -> str:
    """Escape Markdown V2 special characters."""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


def format_time_ms(ms: float) -> str:
    """Format milliseconds into a human-readable string."""
    if ms < 1000:
        return f"{int(ms)}ms"
    elif ms < 60000:
        return f"{ms/1000:.1f}s"
    else:
        return f"{ms/60000:.1f}m"


def format_number(n: int) -> str:
    """Format a number with K/M suffixes."""
    if n < 1000:
        return str(n)
    elif n < 1_000_000:
        return f"{n/1000:.1f}K"
    else:
        return f"{n/1_000_000:.1f}M"


def mask_url(url: str) -> str:
    """Mask the middle of a URL for privacy in logs."""
    if len(url) <= 30:
        return url
    return url[:20] + '...' + url[-10:]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HTML Parsing Helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def extract_meta_refresh(html: str) -> Optional[str]:
    """Extract URL from meta refresh tag."""
    patterns = [
        r'<meta[^>]*http-equiv=["\']refresh["\'][^>]*content=["\'][\d;]*\s*url=(.*?)["\']',
        r'<meta[^>]*content=["\'][\d;]*\s*url=(.*?)["\'][^>]*http-equiv=["\']refresh["\']',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            url = m.group(1).strip()
            if is_valid_url(url):
                return url
    return None


def extract_js_redirects(html: str) -> List[str]:
    """Extract potential redirect URLs from JavaScript in HTML."""
    urls = []
    patterns = [
        # window.location assignments
        r'window\.location\s*(?:\.href)?\s*=\s*["\']([^"\']+)["\']',
        r'window\.location\.replace\s*\(\s*["\']([^"\']+)["\']',
        r'window\.location\.assign\s*\(\s*["\']([^"\']+)["\']',
        r'location\s*(?:\.href)?\s*=\s*["\']([^"\']+)["\']',

        # document.location
        r'document\.location\s*(?:\.href)?\s*=\s*["\']([^"\']+)["\']',

        # window.open
        r'window\.open\s*\(\s*["\']([^"\']+)["\']',

        # var url/link assignments
        r'var\s+(?:url|link|redirect|dest|destination|go)\s*=\s*["\']([^"\']+)["\']',
        r'let\s+(?:url|link|redirect|dest|destination|go)\s*=\s*["\']([^"\']+)["\']',
        r'const\s+(?:url|link|redirect|dest|destination|go)\s*=\s*["\']([^"\']+)["\']',

        # href in JS
        r'\.href\s*=\s*["\']([^"\']+)["\']',

        # setTimeout/setInterval with redirect
        r'setTimeout\s*\(\s*function\s*\(\)\s*\{\s*(?:window\.)?location\s*(?:\.href)?\s*=\s*["\']([^"\']+)["\']',
    ]

    for pat in patterns:
        for m in re.finditer(pat, html, re.IGNORECASE):
            url = m.group(1)
            if is_valid_url(url):
                urls.append(url)

    return urls


def extract_form_action(html: str) -> Optional[str]:
    """Extract the action URL from the first form in HTML."""
    m = re.search(r'<form[^>]*action=["\']([^"\']*)["\']', html, re.IGNORECASE)
    if m:
        return m.group(1)
    return None


def extract_hidden_inputs(html: str) -> dict:
    """Extract all hidden input fields from HTML forms."""
    inputs = {}
    pattern = r'<input[^>]*type=["\']hidden["\'][^>]*/?\s*>'
    for m in re.finditer(pattern, html, re.IGNORECASE):
        tag = m.group(0)
        name_m = re.search(r'name=["\']([^"\']*)["\']', tag)
        value_m = re.search(r'value=["\']([^"\']*)["\']', tag)
        if name_m:
            name = name_m.group(1)
            value = value_m.group(1) if value_m else ''
            inputs[name] = value
    return inputs


def extract_csrf_token(html: str) -> Optional[str]:
    """Extract CSRF token from various common patterns."""
    patterns = [
        r'name=["\']_token["\'][^>]*value=["\']([^"\']+)["\']',
        r'name=["\']csrf[_-]?token["\'][^>]*value=["\']([^"\']+)["\']',
        r'name=["\']csrfmiddlewaretoken["\'][^>]*value=["\']([^"\']+)["\']',
        r'value=["\']([^"\']+)["\'][^>]*name=["\']_token["\']',
        r'<meta\s+name=["\']csrf-token["\']\s+content=["\']([^"\']+)["\']',
        r'window\.csrfToken\s*=\s*["\']([^"\']+)["\']',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def extract_countdown(html: str) -> int:
    """Extract countdown timer value from HTML (in seconds). Returns 0 if not found."""
    patterns = [
        r'var\s+(?:count|timer|countdown|seconds|wait|delay)\s*=\s*(\d+)',
        r'data-(?:seconds|countdown|timer|wait)\s*=\s*["\'](\d+)["\']',
        r'setTimeout\s*\([^,]+,\s*(\d{4,6})\)',  # milliseconds
    ]
    for pat in patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            val = int(m.group(1))
            if val > 1000:  # likely milliseconds
                return val // 1000
            return val
    return 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Base64 & Encoding Detection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def try_base64_decode(text: str) -> Optional[str]:
    """Try to decode a base64-encoded string. Returns decoded URL if valid."""
    import base64
    try:
        # Add padding if needed
        padded = text + '=' * (4 - len(text) % 4) if len(text) % 4 else text
        decoded = base64.b64decode(padded).decode('utf-8', errors='ignore')
        if is_valid_url(decoded):
            return decoded
    except Exception:
        pass
    return None


def try_rot13_decode(text: str) -> Optional[str]:
    """Try ROT13 decoding."""
    import codecs
    try:
        decoded = codecs.decode(text, 'rot_13')
        if is_valid_url(decoded):
            return decoded
    except Exception:
        pass
    return None


def try_hex_decode(text: str) -> Optional[str]:
    """Try hex decoding."""
    try:
        decoded = bytes.fromhex(text).decode('utf-8', errors='ignore')
        if is_valid_url(decoded):
            return decoded
    except Exception:
        pass
    return None

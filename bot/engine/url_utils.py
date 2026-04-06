import re
from urllib.parse import urlparse

def extract_url(text):
    pattern = r'https?://[^\s<>"{}|\^`\[\]]+'
    match = re.search(pattern, text)
    if match:
        return match.group(0).rstrip('.,;:!?)')
    pattern2 = r'(?:[\w-]+\.)+[a-z]{2,}(?:/[^\s]*)?'
    match2 = re.search(pattern2, text, re.IGNORECASE)
    if match2:
        url = match2.group(0)
        if '.' in url:
            return 'https://' + url
    return None

def extract_domain(url):
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except:
        return ""

def truncate(s, n=40):
    return s[:n] + "..." if len(s) > n else s

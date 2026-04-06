import time
from urllib.parse import urlparse
from dataclasses import dataclass
from typing import Optional
from bot.engine.domain_list import KNOWN_SHORTENER_DOMAINS
from bot.engine import layer1_redirect, layer2_patterns, layer3_external_apis, layer4_browser

@dataclass
class BypassResult:
    success: bool
    destination: str = ""
    shortener: str = "Unknown"
    method: str = ""
    time_ms: int = 0
    error: str = ""

class BypassManager:
    def clean_url(self, url):
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        return url

    def extract_domain(self, url):
        try:
            parsed = urlparse(url)
            d = parsed.netloc.lower()
            if d.startswith("www."):
                d = d[4:]
            return d
        except:
            return ""

    def is_shortener_url(self, url):
        domain = self.extract_domain(url)
        return domain in KNOWN_SHORTENER_DOMAINS

    def identify_shortener(self, url):
        domain = self.extract_domain(url)
        return KNOWN_SHORTENER_DOMAINS.get(domain, "Unknown")

    async def bypass(self, url):
        url = self.clean_url(url)
        shortener = self.identify_shortener(url)
        start = time.time()

        # Layer 1: Redirect
        try:
            result = await layer1_redirect.attempt(url)
            if result and result != url and not self.is_shortener_url(result):
                return BypassResult(True, result, shortener, "redirect", int((time.time()-start)*1000))
        except:
            pass

        # Layer 2: Patterns
        try:
            result = await layer2_patterns.attempt(url, shortener)
            if result and result != url:
                return BypassResult(True, result, shortener, "pattern", int((time.time()-start)*1000))
        except:
            pass

        # Layer 3: External APIs
        try:
            result = await layer3_external_apis.attempt(url)
            if result and result != url:
                return BypassResult(True, result, shortener, "api", int((time.time()-start)*1000))
        except:
            pass

        # Layer 4: Browser
        try:
            result = await layer4_browser.attempt(url)
            if result and result != url:
                return BypassResult(True, result, shortener, "browser", int((time.time()-start)*1000))
        except:
            pass

        return BypassResult(False, shortener=shortener, error="Could not bypass. Try again later.")

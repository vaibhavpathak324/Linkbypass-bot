import time
import logging
from urllib.parse import urlparse
from dataclasses import dataclass
from typing import Optional
from bot.engine.domain_list import KNOWN_SHORTENER_DOMAINS
from bot.engine import layer1_redirect, layer2_patterns, layer3_external_apis, layer4_browser

logger = logging.getLogger(__name__)

@dataclass
class BypassResult:
    success: bool
    destination: str = ""
    shortener: str = "Unknown"
    method: str = ""
    time_ms: int = 0
    error: str = ""

def _extract_url_from_result(result):
    """Extract URL string from layer result (handles both dict and string returns)."""
    if result is None:
        return None
    if isinstance(result, dict):
        if result.get("success"):
            return result.get("url")
        return None
    if isinstance(result, str) and result.startswith("http"):
        return result
    return None

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

        # Layer 1: Redirect following
        try:
            logger.info(f"[Layer1] Trying redirect for {url}")
            raw = await layer1_redirect.attempt(url)
            result = _extract_url_from_result(raw)
            if result and result != url and not self.is_shortener_url(result):
                logger.info(f"[Layer1] Success: {result}")
                return BypassResult(True, result, shortener, "redirect", int((time.time()-start)*1000))
        except Exception as e:
            logger.warning(f"[Layer1] Error: {e}")

        # Layer 2: Pattern-based bypass (adlinkfly, linkvertise, ouo, etc.)
        try:
            logger.info(f"[Layer2] Trying patterns for {url}")
            raw = await layer2_patterns.attempt(url, shortener)
            result = _extract_url_from_result(raw)
            if result and result != url:
                logger.info(f"[Layer2] Success: {result}")
                return BypassResult(True, result, shortener, "pattern", int((time.time()-start)*1000))
        except Exception as e:
            logger.warning(f"[Layer2] Error: {e}")

        # Layer 3: External APIs
        try:
            logger.info(f"[Layer3] Trying external APIs for {url}")
            raw = await layer3_external_apis.attempt(url)
            result = _extract_url_from_result(raw)
            if result and result != url:
                logger.info(f"[Layer3] Success: {result}")
                return BypassResult(True, result, shortener, "api", int((time.time()-start)*1000))
        except Exception as e:
            logger.warning(f"[Layer3] Error: {e}")

        # Layer 4: Cloudscraper / browser-like
        try:
            logger.info(f"[Layer4] Trying cloudscraper for {url}")
            raw = await layer4_browser.attempt(url)
            result = _extract_url_from_result(raw)
            if result and result != url and not self.is_shortener_url(result):
                logger.info(f"[Layer4] Success: {result}")
                return BypassResult(True, result, shortener, "browser", int((time.time()-start)*1000))
        except Exception as e:
            logger.warning(f"[Layer4] Error: {e}")

        logger.warning(f"All layers failed for {url}")
        return BypassResult(False, shortener=shortener, error="All bypass methods failed. The link may require CAPTCHA or manual interaction.")

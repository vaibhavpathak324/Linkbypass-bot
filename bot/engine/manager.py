"""
LinkBypass Pro — Bypass Engine Manager v3.1
============================================
6-layer bypass orchestrator with intelligent routing.
CF-aware routing for Cloudflare-protected domains.
"""

import time
import logging
import asyncio
from typing import Optional
from dataclasses import dataclass, field

from bot.config import GLOBAL_BYPASS_TIMEOUT
from bot.engine.url_utils import (
    is_valid_url, get_domain, detect_shortener,
    is_shortener_url, normalize_url, is_destination_url
)
from bot.engine.domain_list import get_shortener_info, get_total_count

logger = logging.getLogger(__name__)

CF_PROTECTED_DOMAINS = {
    "lksfy.com", "linkvertise.com", "link1s.com", "shrinkme.io",
    "shrinkforearn.in", "indianshortner.com", "easysky.in",
    "tnlink.in", "xpshort.com", "dulink.in", "atglinks.com",
    "ez4short.com", "adrinolinks.in", "mdiskshortner.link",
    "shortingly.click", "mplaylink.com", "urlsopen.net",
}

# Layer name -> layer number
LAYER_NUMBERS = {
    "Layer1_Redirect": 1,
    "Layer2_Patterns": 2,
    "Layer3_APIs": 3,
    "Layer4_Cloudscraper": 4,
    "Layer5_Headless": 5,
    "cache": 0,
}


@dataclass
class BypassResult:
    success: bool
    destination_url: Optional[str] = None
    shortener: Optional[str] = None
    method: Optional[str] = None
    time_taken_ms: float = 0.0
    layer: int = 0
    cached: bool = False
    error: Optional[str] = None

    # Aliases for backward compatibility
    @property
    def url(self):
        return self.destination_url


# Module-level cache and stats
_cache: dict = {}
_stats = {"total": 0, "success": 0, "by_layer": {}}


async def _run_layer1(url: str) -> Optional[str]:
    from bot.engine.layer1_redirect import attempt
    return await attempt(url)

async def _run_layer2(url: str) -> Optional[str]:
    from bot.engine.layer2_patterns import attempt
    return await attempt(url)

async def _run_layer3(url: str) -> Optional[str]:
    from bot.engine.layer3_external_apis import attempt
    return await attempt(url)

async def _run_layer4(url: str) -> Optional[str]:
    from bot.engine.layer4_browser import try_cloudscraper_bypass
    return await try_cloudscraper_bypass(url)

async def _run_layer5(url: str) -> Optional[str]:
    from bot.engine.layer5_headless import attempt
    return await attempt(url)


async def bypass_url(url: str, timeout: int = None) -> BypassResult:
    """Main entry point — try each layer in order until one succeeds."""
    global _cache, _stats
    timeout = timeout or GLOBAL_BYPASS_TIMEOUT
    start = time.time()
    _stats["total"] += 1

    url = normalize_url(url)
    if not is_valid_url(url):
        return BypassResult(False, error="Invalid URL")
    if not is_shortener_url(url):
        return BypassResult(False, error="Not a known shortener URL")

    domain = get_domain(url)
    shortener_info = detect_shortener(url)
    if isinstance(shortener_info, tuple):
        shortener = shortener_info[0]
    else:
        shortener = shortener_info or domain

    # Cache hit
    if url in _cache:
        logger.info(f"Cache hit for {url}")
        ms = (time.time() - start) * 1000
        return BypassResult(True, _cache[url], shortener, "cache", ms, 0, True)

    is_cf = domain in CF_PROTECTED_DOMAINS

    if is_cf:
        layers = [
            ("Layer3_APIs", _run_layer3),
            ("Layer4_Cloudscraper", _run_layer4),
            ("Layer5_Headless", _run_layer5),
            ("Layer1_Redirect", _run_layer1),
            ("Layer2_Patterns", _run_layer2),
        ]
    else:
        layers = [
            ("Layer1_Redirect", _run_layer1),
            ("Layer2_Patterns", _run_layer2),
            ("Layer3_APIs", _run_layer3),
            ("Layer4_Cloudscraper", _run_layer4),
            ("Layer5_Headless", _run_layer5),
        ]

    elapsed = lambda: time.time() - start
    for name, runner in layers:
        remaining = timeout - elapsed()
        if remaining <= 0:
            break
        try:
            logger.info(f"[{shortener}] Trying {name} ({remaining:.1f}s left)")
            result = await asyncio.wait_for(runner(url), timeout=min(remaining, 25))
            if result and is_destination_url(result, url):
                took_ms = elapsed() * 1000
                logger.info(f"[{shortener}] {name} succeeded in {took_ms:.0f}ms -> {result}")
                _cache[url] = result
                _stats["success"] += 1
                _stats["by_layer"][name] = _stats["by_layer"].get(name, 0) + 1
                layer_num = LAYER_NUMBERS.get(name, 0)
                return BypassResult(True, result, shortener, name, took_ms, layer_num, False)
        except asyncio.TimeoutError:
            logger.warning(f"[{shortener}] {name} timed out")
        except Exception as e:
            logger.warning(f"[{shortener}] {name} error: {e}")

    return BypassResult(False, shortener=shortener, time_taken_ms=elapsed() * 1000,
                        error="All layers failed")


def get_stats() -> dict:
    return {
        "total": _stats["total"],
        "success": _stats["success"],
        "rate": f"{(_stats['success']/max(1,_stats['total']))*100:.1f}%",
        "by_layer": _stats["by_layer"],
        "cache_size": len(_cache),
        "supported": get_total_count(),
    }

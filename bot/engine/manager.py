"""
LinkBypass Pro — Bypass Engine Manager
========================================
The central orchestrator that coordinates all bypass layers.

Layer Order:
1. Cache Check — instant if cached
2. Layer 1: HTTP Redirects — fastest (< 1s)
3. Layer 2: Pattern-Based — fast (1-5s)  
4. Layer 3: External APIs — medium (3-15s)
5. Layer 4: Playwright Browser — reliable (5-30s)
6. Layer 5: Advanced Multi-Strategy — last resort (5-20s)
"""

import time
import logging
import asyncio
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass

from bot.config import GLOBAL_BYPASS_TIMEOUT
from bot.engine.url_utils import (
    is_valid_url, get_domain, detect_shortener,
    is_shortener_url, normalize_url, is_destination_url
)
from bot.engine.domain_list import get_shortener_info, get_total_count
from bot.database.db import (
    get_cached_bypass, set_cached_bypass,
    update_shortener_stats, get_setting
)

logger = logging.getLogger(__name__)


@dataclass
class BypassResult:
    """Result of a bypass attempt."""
    success: bool
    original_url: str
    destination_url: str = ""
    method: str = "none"
    layer: int = 0
    shortener: str = "unknown"
    time_taken_ms: float = 0
    error: str = ""
    cached: bool = False

    def to_dict(self) -> dict:
        return {
            'success': self.success,
            'original_url': self.original_url,
            'destination_url': self.destination_url,
            'method': self.method,
            'layer': self.layer,
            'shortener': self.shortener,
            'time_taken_ms': round(self.time_taken_ms, 1),
            'error': self.error,
            'cached': self.cached,
        }


# Known Cloudflare-protected shortener domains
CF_PROTECTED_DOMAINS = {
    'lksfy.com', 'linkvertise.com', 'link-to.net', 'direct-link.net',
    'linkvertise.net', 'link-center.net', 'link-target.net',
    'shrinkme.io', 'gplinks.co', 'shareus.io', 'ouo.io', 'ouo.press',
}


async def bypass_url(url: str) -> BypassResult:
    """
    Main bypass function. Takes a URL and returns the destination.
    Tries all layers in order with timeout protection.
    """
    start = time.time()
    url = normalize_url(url)

    if not is_valid_url(url):
        return BypassResult(
            success=False, original_url=url,
            error="Invalid URL", method="validation"
        )

    # Detect shortener
    shortener_name, category = detect_shortener(url)
    domain = get_domain(url)
    logger.info(f"[Manager] Bypass request: {url[:80]} (shortener: {shortener_name}, category: {category})")

    # Check if URL is already a destination (not a shortener)
    if is_destination_url(url):
        return BypassResult(
            success=True, original_url=url,
            destination_url=url, method="direct",
            shortener="none",
            time_taken_ms=(time.time() - start) * 1000
        )

    # Check cache
    cached = await get_cached_bypass(url)
    if cached:
        logger.info(f"[Manager] Cache hit: {cached['destination_url'][:80]}")
        return BypassResult(
            success=True, original_url=url,
            destination_url=cached['destination_url'],
            method=cached['method'], shortener=cached['shortener'],
            time_taken_ms=(time.time() - start) * 1000,
            cached=True
        )

    # Define all layers
    all_layers = [
        (1, "redirect", _try_layer1),
        (2, "pattern", _try_layer2),
        (3, "external_api", _try_layer3),
        (4, "playwright", _try_layer4),
        (5, "advanced", _try_layer5),
    ]

    # Smart layer ordering based on shortener type
    if domain in CF_PROTECTED_DOMAINS or category in ('js_based', 'multi_step', 'encrypted'):
        # CF-protected: try Playwright first, then others
        layers = [
            (4, "playwright", _try_layer4),
            (1, "redirect", _try_layer1),
            (3, "external_api", _try_layer3),
            (2, "pattern", _try_layer2),
            (5, "advanced", _try_layer5),
        ]
    elif category == 'redirect':
        # Simple redirects: HTTP first
        layers = [
            (1, "redirect", _try_layer1),
            (2, "pattern", _try_layer2),
            (4, "playwright", _try_layer4),
            (3, "external_api", _try_layer3),
            (5, "advanced", _try_layer5),
        ]
    else:
        # Default: try all in standard order
        layers = all_layers

    # Try each layer with timeout
    last_error = ""

    for layer_num, method_name, layer_func in layers:
        elapsed = (time.time() - start) * 1000
        if elapsed > GLOBAL_BYPASS_TIMEOUT * 1000:
            logger.warning(f"[Manager] Global timeout reached after {elapsed:.0f}ms")
            break

        try:
            remaining_timeout = max(5, GLOBAL_BYPASS_TIMEOUT - (time.time() - start))
            # Give Playwright more time
            if method_name == "playwright":
                remaining_timeout = min(remaining_timeout, 55)
            else:
                remaining_timeout = min(remaining_timeout, 20)

            logger.info(f"[Manager] Trying Layer {layer_num} ({method_name})")

            result = await asyncio.wait_for(
                layer_func(url),
                timeout=remaining_timeout
            )

            if result and is_valid_url(result):
                time_taken = (time.time() - start) * 1000
                logger.info(
                    f"[Manager] SUCCESS via Layer {layer_num} ({method_name}) "
                    f"in {time_taken:.0f}ms: {result[:80]}"
                )

                # Update stats
                await update_shortener_stats(shortener_name, True, time_taken)

                # Cache the result
                await set_cached_bypass(url, result, method_name, shortener_name)

                return BypassResult(
                    success=True, original_url=url,
                    destination_url=result, method=method_name,
                    layer=layer_num, shortener=shortener_name,
                    time_taken_ms=time_taken
                )

        except asyncio.TimeoutError:
            last_error = f"Layer {layer_num} timeout"
            logger.debug(f"[Manager] Layer {layer_num} timed out")

        except Exception as e:
            last_error = f"Layer {layer_num}: {type(e).__name__}: {str(e)[:100]}"
            logger.debug(f"[Manager] Layer {layer_num} error: {e}")

    # All layers failed
    time_taken = (time.time() - start) * 1000
    await update_shortener_stats(shortener_name, False, error=last_error)

    logger.warning(f"[Manager] All layers failed for {url[:80]} after {time_taken:.0f}ms")

    return BypassResult(
        success=False, original_url=url,
        error=last_error or "All bypass methods failed",
        shortener=shortener_name,
        time_taken_ms=time_taken
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Layer Wrappers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def _try_layer1(url: str) -> Optional[str]:
    """Layer 1: HTTP Redirect Following."""
    from bot.engine.layer1_redirect import attempt
    return await attempt(url)


async def _try_layer2(url: str) -> Optional[str]:
    """Layer 2: Pattern-Based Extraction."""
    from bot.engine.layer2_patterns import attempt
    return await attempt(url)


async def _try_layer3(url: str) -> Optional[str]:
    """Layer 3: External Bypass APIs."""
    from bot.engine.layer3_external_apis import attempt
    return await attempt(url)


async def _try_layer4(url: str) -> Optional[str]:
    """Layer 4: Playwright Browser (real Chromium)."""
    from bot.engine.layer4_browser import attempt
    return await attempt(url)


async def _try_layer5(url: str) -> Optional[str]:
    """Layer 5: Advanced Multi-Strategy."""
    from bot.engine.layer5_headless import attempt
    return await attempt(url)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Batch Bypass
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def bypass_urls(urls: list, max_concurrent: int = 3) -> list:
    """Bypass multiple URLs concurrently."""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _bypass_with_semaphore(url):
        async with semaphore:
            return await bypass_url(url)

    tasks = [_bypass_with_semaphore(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    final = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            final.append(BypassResult(
                success=False, original_url=urls[i],
                error=str(result), method="error"
            ))
        else:
            final.append(result)

    return final


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Stats
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_engine_info() -> dict:
    """Get information about the bypass engine."""
    return {
        'layers': 5,
        'supported_shorteners': get_total_count(),
        'layer_names': {
            1: 'HTTP Redirect',
            2: 'Pattern-Based',
            3: 'External APIs',
            4: 'Playwright Browser',
            5: 'Advanced Multi-Strategy',
        }
    }

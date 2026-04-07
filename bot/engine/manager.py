"""
LinkBypass Pro — Bypass Engine Manager
========================================
The central orchestrator that coordinates all bypass layers.
Tries each layer in order of speed/reliability, with caching,
retry logic, and comprehensive error handling.

Layer Order:
1. Cache Check — instant if cached
2. Layer 1: HTTP Redirects — fastest (< 1s)
3. Layer 2: Pattern-Based — fast (1-5s)
4. Layer 3: External APIs — medium (3-15s)
5. Layer 4: Cloudscraper — slow (5-20s)
6. Layer 5: Advanced Headless — slowest (10-30s)
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

    # Define layers to try
    layers = [
        (1, "redirect", _try_layer1),
        (2, "pattern", _try_layer2),
        (3, "external_api", _try_layer3),
        (4, "cloudscraper", _try_layer4),
    ]

    # Check if layer 5 (headless) is enabled
    headless_enabled = await get_setting('enable_layer5_headless', 'false')
    if headless_enabled == 'true':
        layers.append((5, "headless", _try_layer5))

    # Determine optimal layer order based on shortener info
    info = get_shortener_info(get_domain(url))
    if info:
        preferred_method = info.get('method', 'auto')
        if preferred_method == 'redirect':
            # Keep default order (redirect first)
            pass
        elif preferred_method == 'pattern':
            # Move pattern to first
            layers = [l for l in layers if l[0] == 2] + [l for l in layers if l[0] != 2]
        elif preferred_method == 'api':
            # Try API first
            layers = [l for l in layers if l[0] == 3] + [l for l in layers if l[0] != 3]
        elif preferred_method == 'browser':
            # Try browser first
            layers = [l for l in layers if l[0] == 4] + [l for l in layers if l[0] != 4]

    # Check if API bypass should be preferred
    prefer_api = await get_setting('prefer_api_bypass', 'true')
    if prefer_api == 'true' and category not in ('redirect',):
        # Move API layer up (after current first layer)
        api_layer = [l for l in layers if l[0] == 3]
        other_layers = [l for l in layers if l[0] != 3]
        if api_layer and other_layers:
            layers = [other_layers[0]] + api_layer + other_layers[1:]

    # Try each layer with timeout
    max_retries = int(await get_setting('max_retries', '2'))
    last_error = ""

    for layer_num, method_name, layer_func in layers:
        elapsed = (time.time() - start) * 1000
        if elapsed > GLOBAL_BYPASS_TIMEOUT * 1000:
            logger.warning(f"[Manager] Global timeout reached after {elapsed:.0f}ms")
            break

        for attempt in range(max_retries):
            try:
                remaining_timeout = max(5, GLOBAL_BYPASS_TIMEOUT - (time.time() - start))

                logger.debug(f"[Manager] Trying Layer {layer_num} ({method_name}), attempt {attempt + 1}")

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

                break  # No result but no error, move to next layer

            except asyncio.TimeoutError:
                last_error = f"Layer {layer_num} timeout"
                logger.debug(f"[Manager] Layer {layer_num} timed out")
                break  # Don't retry on timeout, move to next layer

            except Exception as e:
                last_error = f"Layer {layer_num}: {type(e).__name__}: {str(e)[:100]}"
                logger.debug(f"[Manager] Layer {layer_num} error (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5)  # Brief pause before retry

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
    """Layer 4: Cloudscraper Browser."""
    from bot.engine.layer4_browser import attempt
    return await attempt(url)


async def _try_layer5(url: str) -> Optional[str]:
    """Layer 5: Advanced Headless."""
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
            4: 'Cloudscraper',
            5: 'Advanced Headless',
        }
    }

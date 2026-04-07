"""
LinkBypass Pro - Bypass Engine Manager v4.1
=============================================
Intelligent multi-layer bypass orchestration with:
- CF-protected domain detection & priority routing
- Per-layer adaptive timeouts
- Result caching with TTL
"""

import asyncio
import time
import logging
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

@dataclass
class BypassResult:
    success: bool = False
    original_url: str = ""
    destination_url: Optional[str] = None
    time_taken_ms: int = 0
    layer: str = ""
    method: str = ""
    cached: bool = False
    shortener: str = ""
    error: Optional[str] = None

CF_PROTECTED_DOMAINS = {
    'lksfy.com', 'shrinkme.io', 'shrinke.me',
    'ouo.io', 'ouo.press', 'za.gl', 'za.uy',
    'exe.io', 'exey.io', 'fc.lc', 'fc-lc.com',
    'gplinks.co', 'gplinks.in',
    'shrinkforearn.in', 'shrinkearn.com',
    'adshrink.it', 'clicksfly.com', 'clicksfly.in',
    'linkvertise.com', 'linkvertise.net',
    'link1s.com', 'cutty.app', 'cuty.io',
}

_cache = {}
CACHE_TTL = 3600

async def bypass_url(url: str) -> BypassResult:
    start = time.time()
    original_url = url.strip()

    if original_url in _cache:
        cached_result, cached_time = _cache[original_url]
        if time.time() - cached_time < CACHE_TTL:
            cached_result.cached = True
            cached_result.time_taken_ms = int((time.time() - start) * 1000)
            return cached_result

    try:
        domain = urlparse(original_url).netloc.lower().replace('www.', '')
    except Exception:
        domain = ''

    shortener_name = domain.split('.')[0] if domain else 'unknown'
    is_cf = domain in CF_PROTECTED_DOMAINS

    if is_cf:
        # CF-protected: Playwright first (only thing that can beat CF managed challenges)
        # then APIs (some premium ones might work), skip simple layers
        layer_order = [
            ('Layer 5: Headless', _try_layer5, 65),
            ('Layer 3: External APIs', _try_layer3, 30),
            ('Layer 4: Browser Sim', _try_layer4, 25),
        ]
    else:
        # Non-CF: fast layers first
        layer_order = [
            ('Layer 1: Redirects', _try_layer1, 15),
            ('Layer 2: Patterns', _try_layer2, 20),
            ('Layer 3: External APIs', _try_layer3, 30),
            ('Layer 4: Browser Sim', _try_layer4, 25),
            ('Layer 5: Headless', _try_layer5, 50),
        ]

    last_error = "All layers failed"

    for layer_name, layer_func, timeout in layer_order:
        try:
            result_url = await asyncio.wait_for(layer_func(original_url), timeout=timeout)
            if result_url and result_url != original_url:
                elapsed = int((time.time() - start) * 1000)
                result = BypassResult(
                    success=True, original_url=original_url,
                    destination_url=result_url, time_taken_ms=elapsed,
                    layer=layer_name, method=layer_name, cached=False,
                    shortener=shortener_name
                )
                _cache[original_url] = (result, time.time())
                logger.info(f"bypass ok {layer_name} {domain} {elapsed}ms")
                return result
        except asyncio.TimeoutError:
            last_error = f"{layer_name} timed out"
            logger.warning(f"[Manager] {layer_name} timed out for {domain}")
        except Exception as e:
            last_error = f"{layer_name}: {str(e)}"
            logger.warning(f"[Manager] {layer_name} error for {domain}: {e}")

    elapsed = int((time.time() - start) * 1000)
    return BypassResult(success=False, original_url=original_url,
        time_taken_ms=elapsed, layer="none", method="none", error=last_error,
        shortener=shortener_name)

async def _try_layer1(url):
    try:
        from bot.engine.layer1_redirect import attempt
        return await attempt(url)
    except ImportError:
        from bot.engine.layer1_redirect import follow_redirects
        return await follow_redirects(url)
    except Exception:
        return None

async def _try_layer2(url):
    try:
        from bot.engine.layer2_patterns import attempt
        return await attempt(url)
    except ImportError:
        from bot.engine.layer2_patterns import try_pattern_bypass
        return await try_pattern_bypass(url)
    except Exception:
        return None

async def _try_layer3(url):
    try:
        from bot.engine.layer3_external_apis import attempt
        return await attempt(url)
    except Exception as e:
        logger.debug(f"[Manager] Layer3 import/run error: {e}")
        return None

async def _try_layer4(url):
    try:
        from bot.engine.layer4_browser import attempt
        return await attempt(url)
    except Exception as e:
        logger.debug(f"[Manager] Layer4 import/run error: {e}")
        return None

async def _try_layer5(url):
    try:
        from bot.engine.layer5_headless import attempt
        return await attempt(url)
    except Exception as e:
        logger.error(f"[Manager] Layer5 error: {e}")
        return None

SUPPORTED_SHORTENERS = [
    'bit.ly', 'tinyurl.com', 'is.gd', 'lksfy.com', 'shrinkme.io',
    'ouo.io', 'exe.io', 'fc.lc', 'gplinks.co', 'clicksfly.com',
    'linkvertise.com', 'droplink.co', 'mdisk.me', 'shareus.io',
    'adfly', 'shorte.st', 'bc.vc', 'cuty.io', 'cutty.app',
]

def get_total_count():
    return len(SUPPORTED_SHORTENERS)

async def bypass_urls(urls: list, max_concurrent: int = 3) -> list:
    semaphore = asyncio.Semaphore(max_concurrent)
    async def _bypass(url):
        async with semaphore:
            return await bypass_url(url)
    tasks = [_bypass(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    final = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            final.append(BypassResult(success=False, original_url=urls[i],
                error=str(result), method="error"))
        else:
            final.append(result)
    return final

def get_engine_info():
    return {
        'version': '4.1.0',
        'layers': 5,
        'shorteners': '500+',
        'features': ['TLS fingerprinting', 'Headed Playwright + Xvfb', 'Multi-API', 'CloudScraper', 'CF auto-solve'],
    }

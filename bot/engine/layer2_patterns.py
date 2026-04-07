"""
LinkBypass Pro — Layer 2: Pattern-Based Extraction
====================================================
Delegates to site-specific pattern modules for each shortener.
Each pattern module knows how to extract the destination URL
from a specific shortener's HTML/JS structure.
"""

import logging
import importlib
from typing import Optional

from bot.engine.url_utils import get_domain, is_valid_url
from bot.engine.domain_list import get_shortener_info

logger = logging.getLogger(__name__)

# Cache for loaded modules
_module_cache = {}


def _load_pattern_module(module_name: str):
    """Dynamically load a pattern module."""
    if module_name in _module_cache:
        return _module_cache[module_name]

    try:
        mod = importlib.import_module(f"bot.engine.patterns.{module_name}")
        _module_cache[module_name] = mod
        return mod
    except ImportError as e:
        logger.warning(f"[Layer2] Pattern module '{module_name}' not found: {e}")
        return None
    except Exception as e:
        logger.error(f"[Layer2] Error loading module '{module_name}': {e}")
        return None


async def attempt(url: str) -> Optional[str]:
    """
    Attempt to bypass a URL using site-specific patterns.

    This layer:
    1. Detects which shortener the URL belongs to
    2. Loads the appropriate pattern module
    3. Calls the module's bypass function
    4. Falls back to generic patterns if no specific module exists

    Returns the destination URL or None.
    """
    domain = get_domain(url)
    info = get_shortener_info(domain)

    if info and info.get('module'):
        module_name = info['module']
        logger.info(f"[Layer2] Using pattern module '{module_name}' for {domain}")

        mod = _load_pattern_module(module_name)
        if mod and hasattr(mod, 'bypass'):
            try:
                result = await mod.bypass(url)
                if result and is_valid_url(result):
                    logger.info(f"[Layer2] Pattern bypass success: {result[:80]}")
                    return result
            except Exception as e:
                logger.debug(f"[Layer2] Pattern module '{module_name}' error: {e}")

    # Always try generic patterns as fallback
    generic = _load_pattern_module('generic')
    if generic and hasattr(generic, 'bypass'):
        try:
            result = await generic.bypass(url)
            if result and is_valid_url(result):
                logger.info(f"[Layer2] Generic pattern bypass success: {result[:80]}")
                return result
        except Exception as e:
            logger.debug(f"[Layer2] Generic pattern error: {e}")

    return None

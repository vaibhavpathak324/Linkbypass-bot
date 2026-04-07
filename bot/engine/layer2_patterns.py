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

from bot.engine.url_utils import get_domain, detect_shortener
from bot.engine.domain_list import get_shortener_info

logger = logging.getLogger(__name__)

# Pattern module mapping (shortener name -> module name)
PATTERN_MODULES = {
    "adfly": "adfly",
    "adlinkfly": "adlinkfly",
    "gplinks": "gplinks",
    "linkvertise": "linkvertise",
    "ouo": "ouo",
    "shareus": "shareus",
    "shortest": "shortest",
    "bcvc": "bcvc",
    "filepress": "filepress",
    "gdtot": "gdtot",
    "hubcloud": "hubcloud",
    "mdisk": "mdisk",
}


def _load_pattern_module(name: str):
    """Dynamically load a pattern module."""
    try:
        mod = importlib.import_module(f"bot.engine.patterns.{name}")
        return mod
    except ImportError as e:
        logger.debug(f"Pattern module {name} not found: {e}")
        return None
    except Exception as e:
        logger.warning(f"Error loading pattern module {name}: {e}")
        return None


async def attempt(url: str) -> Optional[str]:
    """Try to bypass using a site-specific pattern."""
    domain = get_domain(url)
    shortener = detect_shortener(url)
    info = get_shortener_info(domain)

    # Determine which pattern to try
    pattern_name = None
    if info and info.get("pattern"):
        pattern_name = info["pattern"]
    elif shortener:
        pattern_name = shortener.lower()

    if not pattern_name:
        # Try generic pattern as fallback
        pattern_name = "generic"

    # Check if we have a specific module
    module_name = PATTERN_MODULES.get(pattern_name, pattern_name)
    mod = _load_pattern_module(module_name)

    if mod and hasattr(mod, "bypass"):
        try:
            result = await mod.bypass(url)
            if result:
                logger.info(f"[Layer2] Pattern {pattern_name} succeeded: {result[:80]}")
                return result
        except Exception as e:
            logger.warning(f"[Layer2] Pattern {pattern_name} error: {e}")

    # Try generic as fallback if specific failed
    if module_name != "generic":
        mod = _load_pattern_module("generic")
        if mod and hasattr(mod, "bypass"):
            try:
                result = await mod.bypass(url)
                if result:
                    logger.info(f"[Layer2] Generic pattern succeeded: {result[:80]}")
                    return result
            except Exception as e:
                logger.debug(f"[Layer2] Generic pattern error: {e}")

    return None


# Alias for manager.py import
try_pattern_bypass = attempt

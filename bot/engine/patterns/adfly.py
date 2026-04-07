"""
LinkBypass Pro — Ad.fly Bypass Pattern
========================================
Ad.fly uses a specific obfuscation technique where the destination
URL is encoded in a JavaScript variable called 'ysmm'. The URL is
decoded using a custom algorithm involving base64 and character swapping.
"""

import re
import base64
import logging
from typing import Optional

import httpx

from bot.config import PATTERN_TIMEOUT, USER_AGENTS
from bot.engine.url_utils import is_valid_url, get_domain

logger = logging.getLogger(__name__)


def _decode_ysmm(encoded: str) -> Optional[str]:
    """Decode the ysmm-encoded URL from Ad.fly."""
    try:
        # Step 1: Base64 decode
        decoded_bytes = base64.b64decode(encoded)
        decoded = decoded_bytes.decode('utf-8', errors='ignore')

        # Step 2: Character swap (ad.fly's obfuscation)
        # Split into two halves and interleave
        half = len(decoded) // 2
        part1 = decoded[:half]
        part2 = decoded[half:]

        # Reverse the interleaving
        result = ""
        for i in range(len(part1)):
            result += part1[i]
            if i < len(part2):
                result += part2[i]
        if len(part2) > len(part1):
            result += part2[-1]

        # Step 3: Remove trailing null bytes and clean
        result = result.rstrip('\x00').strip()

        # Step 4: The result should be a URL
        if is_valid_url(result):
            return result

        # Try alternative decode: simple base64
        simple = base64.b64decode(encoded).decode('utf-8', errors='ignore')
        if is_valid_url(simple):
            return simple

    except Exception as e:
        logger.debug(f"[Adfly] ysmm decode error: {e}")

    return None


def _decode_ysmm_v2(encoded: str) -> Optional[str]:
    """Alternative ysmm decoding for newer Ad.fly versions."""
    try:
        # Remove non-base64 characters
        cleaned = re.sub(r'[^A-Za-z0-9+/=]', '', encoded)

        # Add padding
        padding = 4 - len(cleaned) % 4
        if padding != 4:
            cleaned += '=' * padding

        decoded = base64.b64decode(cleaned).decode('utf-8', errors='ignore')

        # Ad.fly v2: XOR with key
        # The decoded string contains pairs of characters
        # Even-index chars form one part, odd-index chars form another
        even = decoded[0::2]
        odd = decoded[1::2]

        # Try both orderings
        for combined in [even + odd, odd + even]:
            if is_valid_url(combined):
                return combined

        # Try direct
        if is_valid_url(decoded):
            return decoded

    except Exception:
        pass

    return None


async def bypass(url: str) -> Optional[str]:
    """Bypass an Ad.fly URL."""
    logger.info(f"[Adfly] Bypassing: {url[:80]}")
    domain = get_domain(url)

    try:
        import random
        async with httpx.AsyncClient(
            timeout=PATTERN_TIMEOUT,
            follow_redirects=False,
            verify=False
        ) as client:
            headers = {
                'User-Agent': random.choice(USER_AGENTS),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.google.com/',
            }

            resp = await client.get(url, headers=headers)

            # Follow initial redirect if any
            if resp.status_code in (301, 302):
                location = resp.headers.get('location', '')
                if location:
                    if get_domain(location) != domain and is_valid_url(location):
                        return location
                    resp = await client.get(location, headers=headers)

            if resp.status_code != 200:
                return None

            html = resp.text

            # Method 1: Extract ysmm variable
            ysmm_match = re.search(r"var\s+ysmm\s*=\s*['\"]([^'\"]+)['\"]", html)
            if ysmm_match:
                encoded = ysmm_match.group(1)
                logger.debug(f"[Adfly] Found ysmm: {encoded[:40]}...")

                # Try both decode methods
                result = _decode_ysmm(encoded)
                if result:
                    logger.info(f"[Adfly] ysmm v1 decode success: {result[:80]}")
                    return result

                result = _decode_ysmm_v2(encoded)
                if result:
                    logger.info(f"[Adfly] ysmm v2 decode success: {result[:80]}")
                    return result

            # Method 2: Extract from HTML directly
            # Some ad.fly clones put the URL in a data attribute
            data_url = re.search(r'data-url=["\']([^"\']+)["\']', html)
            if data_url:
                found = data_url.group(1)
                if is_valid_url(found) and get_domain(found) != domain:
                    return found

            # Method 3: Look for the skip ad link
            skip_patterns = [
                r'<a[^>]*id=["\']skip["\'][^>]*href=["\']([^"\']+)["\']',
                r'<a[^>]*class=["\'][^"\']*skip[^"\']*["\'][^>]*href=["\']([^"\']+)["\']',
                r'<a[^>]*href=["\']([^"\']+)["\'][^>]*id=["\']skip["\']',
            ]
            for pat in skip_patterns:
                m = re.search(pat, html, re.IGNORECASE)
                if m:
                    found = m.group(1)
                    if is_valid_url(found) and get_domain(found) != domain:
                        return found

            # Method 4: Check for countdown URL in JS
            countdown_url = re.search(
                r'(?:countdown_url|getlink|skiplink|dest)\s*=\s*["\']([^"\']+)["\']',
                html, re.IGNORECASE
            )
            if countdown_url:
                found = countdown_url.group(1)
                if is_valid_url(found) and get_domain(found) != domain:
                    return found

    except Exception as e:
        logger.debug(f"[Adfly] Error: {e}")

    return None

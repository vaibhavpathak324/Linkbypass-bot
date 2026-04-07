"""
LinkBypass Pro — OUO.io Bypass Pattern
========================================
OUO.io uses a multi-step form bypass:
1. GET the short URL -> redirects to /go/ page
2. Extract CSRF token from the form
3. POST to /go/ to get to the final page
4. Extract destination from the final page/redirect
"""

import re
import logging
import random
from typing import Optional
from urllib.parse import urljoin

import httpx

from bot.config import PATTERN_TIMEOUT, USER_AGENTS
from bot.engine.url_utils import (
    is_valid_url, get_domain, extract_csrf_token,
    extract_hidden_inputs, extract_js_redirects
)

logger = logging.getLogger(__name__)


async def bypass(url: str) -> Optional[str]:
    """Bypass an OUO.io URL through multi-step form submission."""
    logger.info(f"[OUO] Bypassing: {url[:80]}")
    domain = get_domain(url)

    try:
        async with httpx.AsyncClient(
            timeout=PATTERN_TIMEOUT,
            follow_redirects=False,
            verify=False,
        ) as client:
            headers = {
                'User-Agent': random.choice(USER_AGENTS),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.google.com/',
            }

            # Step 1: GET the short URL
            resp = await client.get(url, headers=headers)

            # Follow redirects within ouo.io
            current_url = url
            for _ in range(5):
                if resp.status_code in (301, 302, 303, 307):
                    location = resp.headers.get('location', '')
                    if not location:
                        break
                    if not location.startswith('http'):
                        location = urljoin(current_url, location)

                    if get_domain(location) != domain and is_valid_url(location):
                        logger.info(f"[OUO] Direct redirect to destination: {location[:80]}")
                        return location

                    current_url = location
                    headers['Referer'] = url
                    resp = await client.get(current_url, headers=headers)
                else:
                    break

            if resp.status_code != 200:
                return None

            html = resp.text

            # Step 2: Extract form data and CSRF token
            csrf = extract_csrf_token(html)
            hidden = extract_hidden_inputs(html)

            if csrf:
                hidden['_token'] = csrf

            # Check if there's a recaptcha — if so, we may need external API
            has_recaptcha = 'g-recaptcha' in html or 'recaptcha' in html.lower()
            if has_recaptcha:
                logger.debug("[OUO] Page has reCAPTCHA — trying without it")

            # Step 3: POST the form
            form_action = current_url  # OUO posts to the same /go/ URL

            # Find the actual form action
            action_match = re.search(r'<form[^>]*action=["\']([^"\']*)["\']', html, re.IGNORECASE)
            if action_match:
                fa = action_match.group(1)
                if fa:
                    form_action = fa if fa.startswith('http') else urljoin(current_url, fa)

            headers['Referer'] = current_url
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
            headers['Origin'] = f"https://{domain}"

            resp2 = await client.post(form_action, data=hidden, headers=headers)

            # Check for redirect
            if resp2.status_code in (301, 302, 303, 307):
                location = resp2.headers.get('location', '')
                if location and is_valid_url(location) and get_domain(location) != domain:
                    logger.info(f"[OUO] Form redirect to destination: {location[:80]}")
                    return location

                # Follow the redirect within OUO
                if location:
                    if not location.startswith('http'):
                        location = urljoin(form_action, location)
                    resp3 = await client.get(location, headers={
                        'User-Agent': headers['User-Agent'],
                        'Referer': form_action,
                    })

                    if resp3.status_code in (301, 302):
                        final_loc = resp3.headers.get('location', '')
                        if final_loc and is_valid_url(final_loc) and get_domain(final_loc) != domain:
                            return final_loc

                    if resp3.status_code == 200:
                        # Second form submission
                        html3 = resp3.text
                        csrf3 = extract_csrf_token(html3)
                        hidden3 = extract_hidden_inputs(html3)
                        if csrf3:
                            hidden3['_token'] = csrf3

                        resp4 = await client.post(
                            str(resp3.url),
                            data=hidden3,
                            headers={
                                'User-Agent': headers['User-Agent'],
                                'Referer': str(resp3.url),
                                'Content-Type': 'application/x-www-form-urlencoded',
                                'Origin': f"https://{domain}",
                            }
                        )

                        if resp4.status_code in (301, 302):
                            final = resp4.headers.get('location', '')
                            if final and is_valid_url(final) and get_domain(final) != domain:
                                return final

            # Check response body for URLs
            if resp2.status_code == 200:
                for u in extract_js_redirects(resp2.text[:20000]):
                    if get_domain(u) != domain and is_valid_url(u):
                        return u

    except Exception as e:
        logger.debug(f"[OUO] Error: {e}")

    return None

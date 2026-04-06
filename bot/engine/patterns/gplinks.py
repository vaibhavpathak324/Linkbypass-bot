import logging
from bot.engine.patterns.adlinkfly import bypass as adlinkfly_bypass

logger = logging.getLogger(__name__)

DOMAINS = [
    "gplinks.com", "gplinks.in", "gplinks.co"
]

async def bypass(url):
    return await adlinkfly_bypass(url)

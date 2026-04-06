from bot.engine.url_utils import extract_domain
from bot.engine.patterns import adlinkfly, linkvertise, ouo, adfly, generic, gplinks, shareus

HANDLERS = {}

def build_handler_map():
    global HANDLERS
    modules = [gplinks, adlinkfly, linkvertise, ouo, adfly, shareus, generic]
    for mod in modules:
        if hasattr(mod, 'DOMAINS'):
            for d in mod.DOMAINS:
                HANDLERS[d] = mod

build_handler_map()

async def attempt(url, shortener_name=None):
    domain = extract_domain(url)
    handler = HANDLERS.get(domain)
    if handler:
        try:
            result = await handler.bypass(url)
            if result and result != url:
                return result
        except Exception:
            pass
    try:
        result = await adlinkfly.bypass(url)
        if result and result != url:
            return result
    except Exception:
        pass
    try:
        result = await generic.bypass(url)
        if result and result != url:
            return result
    except Exception:
        pass
    return None

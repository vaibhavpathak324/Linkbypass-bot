"""
LinkBypass Pro — Shortener Domain Catalog
==========================================
Comprehensive catalog of 500+ known URL shortener domains
with their bypass methods, categories, and pattern modules.

Categories:
- adlinkfly: Sites built on AdLinkFly CMS (most common)
- redirect: Simple HTTP redirect shorteners
- js_based: JavaScript-based redirects
- multi_step: Multi-page/step bypass required
- api_based: Has known API endpoints
- encrypted: Uses encryption/obfuscation
- custom: Custom implementation per site

Bypass Methods:
- auto: Try all layers automatically
- redirect: Simple redirect follow (Layer 1)
- pattern: Use site-specific pattern (Layer 2)
- api: Use external bypass API (Layer 3)
- browser: Use cloudscraper/requests (Layer 4)
- headless: Use headless browser (Layer 5)
"""

import logging
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Domain Database
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

KNOWN_SHORTENER_DOMAINS: Dict[str, dict] = {

    # ── AdLinkFly CMS Sites ─────────────────────────────────
    # AdLinkFly is the most popular URL shortener CMS. These sites
    # share a common bypass pattern: POST to the link page with form tokens.

    "shrinkme.io": {"name": "ShrinkMe", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "shrinkme.org": {"name": "ShrinkMe", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "shrinke.me": {"name": "ShrinkMe", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "gplinks.co": {"name": "GPLinks", "category": "adlinkfly", "method": "pattern", "module": "gplinks"},
    "gplinks.com": {"name": "GPLinks", "category": "adlinkfly", "method": "pattern", "module": "gplinks"},
    "gplinks.in": {"name": "GPLinks", "category": "adlinkfly", "method": "pattern", "module": "gplinks"},
    "shareus.io": {"name": "ShareUs", "category": "adlinkfly", "method": "pattern", "module": "shareus"},
    "shareus.in": {"name": "ShareUs", "category": "adlinkfly", "method": "pattern", "module": "shareus"},
    "share-us.click": {"name": "ShareUs", "category": "adlinkfly", "method": "pattern", "module": "shareus"},
    "droplink.co": {"name": "DropLink", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "droplinks.co": {"name": "DropLink", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "drop.download": {"name": "DropLink", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "adrinolinks.com": {"name": "AdrinoLinks", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "adrinolinks.in": {"name": "AdrinoLinks", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "ez4short.com": {"name": "Ez4Short", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "ez4links.com": {"name": "Ez4Short", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "easysky.in": {"name": "EasySky", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "indianshortner.com": {"name": "IndianShortner", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "inshortner.com": {"name": "IndianShortner", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "dulink.in": {"name": "DuLink", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "du-link.in": {"name": "DuLink", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "gyanilinks.com": {"name": "GyaniLinks", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "gyanilinks.in": {"name": "GyaniLinks", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "rocklinks.net": {"name": "RockLinks", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "rocklinks.in": {"name": "RockLinks", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "link.tnvalue.in": {"name": "TNValue", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "tnlink.in": {"name": "TNLink", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "tnvalue.in": {"name": "TNValue", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "kfrfrlinks.com": {"name": "KFRFRLinks", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "linkshortify.com": {"name": "LinkShortify", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "earnl.xyz": {"name": "Earnl", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "earnl.in": {"name": "Earnl", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "moneykamalo.com": {"name": "MoneyKamalo", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "pkin.me": {"name": "Pkin", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "bindaaslinks.com": {"name": "BindaasLinks", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "runurl.in": {"name": "RunURL", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "flashlink.in": {"name": "FlashLink", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "srt.am": {"name": "SRT", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "tinyfy.in": {"name": "TinyFy", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "urlty.in": {"name": "Urlty", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "linksly.co": {"name": "LinksLy", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "shortingly.in": {"name": "Shortingly", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "shorteet.com": {"name": "Shorteet", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "techymozo.com": {"name": "TechyMozo", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "v.gd": {"name": "VGD", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "htpmovies.click": {"name": "HTPMovies", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "htpmovies.lol": {"name": "HTPMovies", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "htpmovies.art": {"name": "HTPMovies", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "techoreels.com": {"name": "TechoReels", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "dalink.in": {"name": "DaLink", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "dalinks.in": {"name": "DaLink", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "vearnl.in": {"name": "Vearnl", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "atglinks.com": {"name": "ATGLinks", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "gadgetrites.com": {"name": "GadgetRites", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "go.bloggingaro.com": {"name": "BloggingAro", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "go.themeslide.com": {"name": "ThemeSlide", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "go.flashlinks.in": {"name": "FlashLinks", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "link.vipurl.in": {"name": "VipURL", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "xpshort.com": {"name": "XPShort", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "shrinkforearn.in": {"name": "ShrinkForEarn", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "urlshortx.com": {"name": "URLShortX", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "shorte.top": {"name": "Shorte.top", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "adshrink.it": {"name": "AdShrink", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "link1s.com": {"name": "Link1s", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "cuturl.cc": {"name": "CutURL", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "short.pe": {"name": "ShortPE", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "psa.pm": {"name": "PSA", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "clk.sh": {"name": "ClkSh", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "za.gl": {"name": "ZaGL", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "za.uy": {"name": "ZaUY", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "cpm.link": {"name": "CPMLink", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "exe.io": {"name": "Exe.io", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "exey.io": {"name": "Exey.io", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "fc.lc": {"name": "FC.LC", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "fc-lc.com": {"name": "FC.LC", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "al.ly": {"name": "Al.ly", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "ally.sh": {"name": "Ally", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "sfrfrlinks.com": {"name": "SFRFRLinks", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "try2link.com": {"name": "Try2Link", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "try2links.com": {"name": "Try2Link", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},

    # ── Ad.fly Family ─────────────────────────────────────────
    "adf.ly": {"name": "Adfly", "category": "encrypted", "method": "pattern", "module": "adfly"},
    "j.gs": {"name": "Adfly", "category": "encrypted", "method": "pattern", "module": "adfly"},
    "q.gs": {"name": "Adfly", "category": "encrypted", "method": "pattern", "module": "adfly"},
    "ay.gy": {"name": "Adfly", "category": "encrypted", "method": "pattern", "module": "adfly"},
    "atominik.com": {"name": "Adfly", "category": "encrypted", "method": "pattern", "module": "adfly"},
    "tinyium.com": {"name": "Adfly", "category": "encrypted", "method": "pattern", "module": "adfly"},
    "microify.com": {"name": "Adfly", "category": "encrypted", "method": "pattern", "module": "adfly"},
    "adfoc.us": {"name": "Adfocus", "category": "encrypted", "method": "pattern", "module": "adfly"},

    # ── OUO.io Family ────────────────────────────────────────
    "ouo.io": {"name": "OUO", "category": "multi_step", "method": "pattern", "module": "ouo"},
    "ouo.press": {"name": "OUO", "category": "multi_step", "method": "pattern", "module": "ouo"},

    # ── Linkvertise Family ────────────────────────────────────
    "linkvertise.com": {"name": "Linkvertise", "category": "js_based", "method": "pattern", "module": "linkvertise"},
    "linkvertise.net": {"name": "Linkvertise", "category": "js_based", "method": "pattern", "module": "linkvertise"},
    "link-target.net": {"name": "Linkvertise", "category": "js_based", "method": "pattern", "module": "linkvertise"},
    "link-hub.net": {"name": "Linkvertise", "category": "js_based", "method": "pattern", "module": "linkvertise"},
    "link-to.net": {"name": "Linkvertise", "category": "js_based", "method": "pattern", "module": "linkvertise"},
    "direct-link.net": {"name": "Linkvertise", "category": "js_based", "method": "pattern", "module": "linkvertise"},
    "up-to-down.net": {"name": "Linkvertise", "category": "js_based", "method": "pattern", "module": "linkvertise"},
    "lnkload.com": {"name": "Linkvertise", "category": "js_based", "method": "pattern", "module": "linkvertise"},
    "lnk.parts": {"name": "Linkvertise", "category": "js_based", "method": "pattern", "module": "linkvertise"},

    # ── Shorte.st Family ──────────────────────────────────────
    "shorte.st": {"name": "Shortest", "category": "js_based", "method": "pattern", "module": "shortest"},
    "sh.st": {"name": "Shortest", "category": "js_based", "method": "pattern", "module": "shortest"},
    "gestyy.com": {"name": "Shortest", "category": "js_based", "method": "pattern", "module": "shortest"},
    "ceesty.com": {"name": "Shortest", "category": "js_based", "method": "pattern", "module": "shortest"},

    # ── Simple Redirect Shorteners ─────────────────────────────
    "bit.ly": {"name": "Bitly", "category": "redirect", "method": "redirect"},
    "bitly.com": {"name": "Bitly", "category": "redirect", "method": "redirect"},
    "tinyurl.com": {"name": "TinyURL", "category": "redirect", "method": "redirect"},
    "t.co": {"name": "Twitter", "category": "redirect", "method": "redirect"},
    "goo.gl": {"name": "Google", "category": "redirect", "method": "redirect"},
    "ow.ly": {"name": "Hootsuite", "category": "redirect", "method": "redirect"},
    "buff.ly": {"name": "Buffer", "category": "redirect", "method": "redirect"},
    "dlvr.it": {"name": "Dlvr", "category": "redirect", "method": "redirect"},
    "is.gd": {"name": "IsGD", "category": "redirect", "method": "redirect"},
    "rb.gy": {"name": "Rebrandly", "category": "redirect", "method": "redirect"},
    "cutt.ly": {"name": "Cuttly", "category": "redirect", "method": "redirect"},
    "cutt.us": {"name": "Cuttly", "category": "redirect", "method": "redirect"},
    "s.id": {"name": "SID", "category": "redirect", "method": "redirect"},
    "t.ly": {"name": "TLY", "category": "redirect", "method": "redirect"},
    "shorturl.at": {"name": "ShortURL", "category": "redirect", "method": "redirect"},
    "shorturl.me": {"name": "ShortURL", "category": "redirect", "method": "redirect"},
    "tiny.cc": {"name": "TinyCC", "category": "redirect", "method": "redirect"},
    "soo.gd": {"name": "SooGD", "category": "redirect", "method": "redirect"},
    "u.to": {"name": "UTo", "category": "redirect", "method": "redirect"},
    "t2m.io": {"name": "T2M", "category": "redirect", "method": "redirect"},
    "clck.ru": {"name": "Clck", "category": "redirect", "method": "redirect"},
    "dub.sh": {"name": "Dub", "category": "redirect", "method": "redirect"},
    "dub.co": {"name": "Dub", "category": "redirect", "method": "redirect"},
    "short.io": {"name": "ShortIO", "category": "redirect", "method": "redirect"},
    "rebrand.ly": {"name": "Rebrandly", "category": "redirect", "method": "redirect"},
    "bl.ink": {"name": "BLink", "category": "redirect", "method": "redirect"},
    "qr.ae": {"name": "Quora", "category": "redirect", "method": "redirect"},
    "lnkd.in": {"name": "LinkedIn", "category": "redirect", "method": "redirect"},
    "youtu.be": {"name": "YouTube", "category": "redirect", "method": "redirect"},
    "amzn.to": {"name": "Amazon", "category": "redirect", "method": "redirect"},
    "amzn.com": {"name": "Amazon", "category": "redirect", "method": "redirect"},
    "redd.it": {"name": "Reddit", "category": "redirect", "method": "redirect"},
    "wp.me": {"name": "WordPress", "category": "redirect", "method": "redirect"},
    "surl.li": {"name": "SURL", "category": "redirect", "method": "redirect"},
    "linktr.ee": {"name": "Linktree", "category": "redirect", "method": "redirect"},
    "zpr.io": {"name": "Zapier", "category": "redirect", "method": "redirect"},
    "cli.re": {"name": "ClickMeter", "category": "redirect", "method": "redirect"},
    "mcaf.ee": {"name": "McAfee", "category": "redirect", "method": "redirect"},
    "po.st": {"name": "Post", "category": "redirect", "method": "redirect"},

    # ── Indian Shorteners (popular for piracy/movie sites) ────
    "atglinks.com": {"name": "ATGLinks", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "tnvalue.in": {"name": "TNValue", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "247short.com": {"name": "247Short", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "mdiskshortner.link": {"name": "MDiskShort", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "tamizhmasters.com": {"name": "TamizhMasters", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "link.tamizhmasters.com": {"name": "TamizhMasters", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "tamilmv.click": {"name": "TamilMV", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "moviesdaweb.in": {"name": "MoviesDaWeb", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "mobi2c.com": {"name": "Mobi2c", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "100short.com": {"name": "100Short", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "slink.fun": {"name": "SLink", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "powerlinks.site": {"name": "PowerLinks", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "link.vipurl.in": {"name": "VipURL", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "adbull.me": {"name": "AdBull", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "coinlinks.bid": {"name": "CoinLinks", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "coinifly.com": {"name": "CoinIfy", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "mplaylink.com": {"name": "MPlayLink", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "ola-short.com": {"name": "OlaShort", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "tekcrypt.com": {"name": "TekCrypt", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "xpshort.com": {"name": "XPShort", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "go.joinandplay.me": {"name": "JoinAndPlay", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "go.grfrfrlinks.com": {"name": "GRFRFRLinks", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "go.kfrfrlinks.com": {"name": "KFRFRLinks", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},

    # ── MDisk / TeraBox / Cloud Shorteners ────────────────────
    "mdisk.me": {"name": "MDisk", "category": "api_based", "method": "pattern", "module": "mdisk"},
    "mdisk.pro": {"name": "MDisk", "category": "api_based", "method": "pattern", "module": "mdisk"},
    "mdiskpro.in": {"name": "MDisk", "category": "api_based", "method": "pattern", "module": "mdisk"},
    "mdiskpro.com": {"name": "MDisk", "category": "api_based", "method": "pattern", "module": "mdisk"},
    "terabox.com": {"name": "TeraBox", "category": "api_based", "method": "browser"},
    "teraboxapp.com": {"name": "TeraBox", "category": "api_based", "method": "browser"},
    "1024tera.com": {"name": "TeraBox", "category": "api_based", "method": "browser"},

    # ── GDTot / HubCloud / FilePress ──────────────────────────
    "gdtot.pro": {"name": "GDTot", "category": "custom", "method": "pattern", "module": "gdtot"},
    "gdtot.cfd": {"name": "GDTot", "category": "custom", "method": "pattern", "module": "gdtot"},
    "new1.gdtot.sbs": {"name": "GDTot", "category": "custom", "method": "pattern", "module": "gdtot"},
    "gdtot.nl": {"name": "GDTot", "category": "custom", "method": "pattern", "module": "gdtot"},
    "hubcloud.lol": {"name": "HubCloud", "category": "custom", "method": "pattern", "module": "hubcloud"},
    "hubcloud.art": {"name": "HubCloud", "category": "custom", "method": "pattern", "module": "hubcloud"},
    "hubcloud.biz": {"name": "HubCloud", "category": "custom", "method": "pattern", "module": "hubcloud"},
    "hubcloud.in": {"name": "HubCloud", "category": "custom", "method": "pattern", "module": "hubcloud"},
    "filepress.top": {"name": "FilePress", "category": "custom", "method": "pattern", "module": "filepress"},
    "filepress.store": {"name": "FilePress", "category": "custom", "method": "pattern", "module": "filepress"},
    "filepress.click": {"name": "FilePress", "category": "custom", "method": "pattern", "module": "filepress"},

    # ── AroLinks / MoneyCut / PayMe ──────────────────────────
    "arolinks.com": {"name": "AroLinks", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "arolinks.in": {"name": "AroLinks", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "moneycut.net": {"name": "MoneyCut", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "payme.link": {"name": "PayMe", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},

    # ── URL Monetization Networks ────────────────────────────
    "adf.ly": {"name": "Adfly", "category": "encrypted", "method": "pattern", "module": "adfly"},
    "shorte.st": {"name": "Shortest", "category": "js_based", "method": "pattern", "module": "shortest"},
    "bc.vc": {"name": "BCVC", "category": "multi_step", "method": "pattern", "module": "bcvc"},
    "shortzon.com": {"name": "Shortzon", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "tei.ai": {"name": "TeiAI", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "tii.ai": {"name": "TiiAI", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "tei.io": {"name": "TeiIO", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "link.tl": {"name": "LinkTL", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "adfoc.us": {"name": "Adfocus", "category": "js_based", "method": "pattern", "module": "adfly"},
    "admy.link": {"name": "AdMyLink", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "clicksfly.com": {"name": "ClicksFly", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "clicksfly.in": {"name": "ClicksFly", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},

    # ── Blog/WordPress Shorteners ────────────────────────────
    "teknoreel.com": {"name": "TeknoReel", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "techymozo.com": {"name": "TechyMozo", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "links.techymozo.com": {"name": "TechyMozo", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "tglink.in": {"name": "TGLink", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "telegram.me.in": {"name": "TelegramMeIn", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "mytechmint.com": {"name": "MyTechMint", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},

    # ── International Shorteners ──────────────────────────────
    "exe.app": {"name": "ExeApp", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "short-url.link": {"name": "ShortURL", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "mfrfrlinks.com": {"name": "MFRFRLinks", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "shortpay.net": {"name": "ShortPay", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "kfrfrlinks.com": {"name": "KFRFRLinks", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "grfrfrlinks.com": {"name": "GRFRFRLinks", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "rslinks.net": {"name": "RSLinks", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},

    # ── URL Rotators / Paste Sites used as shorteners ─────────
    "pixeldrain.com": {"name": "PixelDrain", "category": "redirect", "method": "redirect"},
    "krakenfiles.com": {"name": "KrakenFiles", "category": "redirect", "method": "redirect"},
    "gofile.io": {"name": "GoFile", "category": "redirect", "method": "redirect"},
    "racaty.io": {"name": "Racaty", "category": "redirect", "method": "redirect"},
    "racaty.net": {"name": "Racaty", "category": "redirect", "method": "redirect"},

    # ── Misc Shorteners ──────────────────────────────────────
    "qlinks.eu": {"name": "QLinks", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "promo-visits.site": {"name": "PromoVisits", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "go.vailink.com": {"name": "VaiLink", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "shorten.is": {"name": "ShortenIs", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "link.bfrfrlinks.com": {"name": "BFRFRLinks", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "gfrfrlinks.com": {"name": "GFRFRLinks", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "short2url.in": {"name": "Short2URL", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "link4earn.com": {"name": "Link4Earn", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "earn4link.in": {"name": "Earn4Link", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "up4cash.com": {"name": "Up4Cash", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "shortzzy.com": {"name": "Shortzzy", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "shortzzy.in": {"name": "Shortzzy", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "go.shortzzy.in": {"name": "Shortzzy", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "newshortzzy.in": {"name": "NewShortzzy", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "shrinkpay.in": {"name": "ShrinkPay", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "linkpays.in": {"name": "LinkPays", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "viralshort.com": {"name": "ViralShort", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "lksfy.com": {"name": "LksFy", "category": "adlinkfly", "method": "headless", "module": "adlinkfly", "cf_protected": True},
    "bfrfrlinks.com": {"name": "BFRFRLinks", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "earnlink.io": {"name": "EarnLink", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "go.earnlink.io": {"name": "EarnLink", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "linkpays.net": {"name": "LinkPays", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "go.adly.pw": {"name": "AdlyPW", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "go.linkto.site": {"name": "LinkToSite", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "cutty.app": {"name": "CuttyApp", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "url.adtival.network": {"name": "Adtival", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},
    "cuty.io": {"name": "CutyIO", "category": "adlinkfly", "method": "pattern", "module": "adlinkfly"},

    # ── Link Protection / Locker Sites ───────────────────────
    "linklock.in": {"name": "LinkLock", "category": "multi_step", "method": "browser"},
    "linksprotector.com": {"name": "LinksProtector", "category": "multi_step", "method": "browser"},
    "safe.mn": {"name": "SafeMN", "category": "multi_step", "method": "browser"},

    # ── Social Media Shorteners ──────────────────────────────
    "instagram.com": {"name": "Instagram", "category": "redirect", "method": "redirect"},
    "fb.me": {"name": "Facebook", "category": "redirect", "method": "redirect"},
    "tiktok.com": {"name": "TikTok", "category": "redirect", "method": "redirect"},
    "pin.it": {"name": "Pinterest", "category": "redirect", "method": "redirect"},
    "vk.cc": {"name": "VK", "category": "redirect", "method": "redirect"},
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Lookup Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_shortener_info(domain: str) -> Optional[dict]:
    """Look up a domain in the shortener database."""
    domain = domain.lower().strip()
    if domain.startswith('www.'):
        domain = domain[4:]

    # Direct lookup
    if domain in KNOWN_SHORTENER_DOMAINS:
        return KNOWN_SHORTENER_DOMAINS[domain]

    # Check subdomains: e.g., go.example.com -> try example.com too
    parts = domain.split('.')
    if len(parts) > 2:
        parent = '.'.join(parts[1:])
        if parent in KNOWN_SHORTENER_DOMAINS:
            return KNOWN_SHORTENER_DOMAINS[parent]

    # Check with subdomain prefix
    for known_domain, info in KNOWN_SHORTENER_DOMAINS.items():
        if domain.endswith('.' + known_domain):
            return info

    return None


def get_all_domains() -> List[str]:
    """Get all known shortener domains."""
    return list(KNOWN_SHORTENER_DOMAINS.keys())


def get_domains_by_category(category: str) -> List[str]:
    """Get domains filtered by category."""
    return [
        d for d, info in KNOWN_SHORTENER_DOMAINS.items()
        if info.get('category') == category
    ]


def get_domains_by_module(module: str) -> List[str]:
    """Get domains that use a specific bypass module."""
    return [
        d for d, info in KNOWN_SHORTENER_DOMAINS.items()
        if info.get('module') == module
    ]


def get_total_count() -> int:
    """Get total number of known shortener domains."""
    return len(KNOWN_SHORTENER_DOMAINS)


def get_category_counts() -> dict:
    """Get count of domains per category."""
    counts = {}
    for info in KNOWN_SHORTENER_DOMAINS.values():
        cat = info.get('category', 'unknown')
        counts[cat] = counts.get(cat, 0) + 1
    return counts

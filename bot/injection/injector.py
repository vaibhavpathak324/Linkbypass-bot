import httpx
import random
from bot.database.db import get_active_shortener_configs, get_setting, increment_shortener_links

class LinkInjector:
    def __init__(self):
        self.counter = 0

    async def inject(self, destination_url, user_is_premium):
        enabled = await get_setting("inject_links_enabled")
        if user_is_premium or enabled != "true":
            return {"final_url": destination_url, "is_direct": True, "shortener_used": None}

        configs = await get_active_shortener_configs()
        if not configs:
            return {"final_url": destination_url, "is_direct": True, "shortener_used": None}

        rotation = await get_setting("shortener_rotation_mode") or "round_robin"
        if rotation == "random":
            config = random.choice(configs)
        elif rotation == "priority":
            config = configs[0]
        else:
            config = configs[self.counter % len(configs)]
            self.counter += 1

        short = await self._create(destination_url, config)
        if short:
            await increment_shortener_links(config["id"])
            return {"final_url": short, "is_direct": False, "shortener_used": config["display_name"]}

        for fallback in configs:
            if fallback["id"] != config["id"]:
                short = await self._create(destination_url, fallback)
                if short:
                    await increment_shortener_links(fallback["id"])
                    return {"final_url": short, "is_direct": False, "shortener_used": fallback["display_name"]}

        return {"final_url": destination_url, "is_direct": True, "shortener_used": None}

    async def _create(self, url, config):
        try:
            api_url = config["api_endpoint"].replace("{key}", config["api_key"]).replace("{url}", url)
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(api_url)
                if resp.status_code == 200:
                    fmt = config["api_format"]
                    if fmt == "plain_text":
                        t = resp.text.strip()
                        return t if t.startswith("http") else None
                    try:
                        data = resp.json()
                        if fmt == "json_shortenedUrl":
                            return data.get("shortenedUrl") or data.get("shortened_url")
                        elif fmt == "json_short_url":
                            return data.get("short_url")
                        elif fmt == "json_data_url":
                            return (data.get("data") or {}).get("url")
                        else:
                            for k in ["shortenedUrl","shortened_url","short_url","result","url","link","short_link"]:
                                if k in data:
                                    return data[k]
                            if "data" in data and isinstance(data["data"], dict):
                                for k in ["url","link","short_url"]:
                                    if k in data["data"]:
                                        return data["data"][k]
                    except:
                        t = resp.text.strip()
                        if t.startswith("http"):
                            return t
        except:
            pass
        return None

link_injector = LinkInjector()

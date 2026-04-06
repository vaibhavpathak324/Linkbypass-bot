import httpx
import re
from bs4 import BeautifulSoup

DOMAINS = ["ouo.io", "ouo.press"]

async def bypass(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://ouo.io/",
        }
        async with httpx.AsyncClient(follow_redirects=False, timeout=20.0, headers=headers, verify=False) as client:
            resp = await client.get(url)
            
            # Follow to the go page
            if resp.status_code in (301, 302):
                next_url = resp.headers.get("location", "")
                if next_url:
                    resp = await client.get(next_url)
            
            soup = BeautifulSoup(resp.text, "html.parser")
            form = soup.find("form", {"method": "POST"})
            if form:
                action = form.get("action", "")
                data = {}
                for inp in form.find_all("input"):
                    name = inp.get("name")
                    if name:
                        data[name] = inp.get("value", "")
                
                resp2 = await client.post(action, data=data, follow_redirects=False)
                if resp2.status_code in (301, 302):
                    dest = resp2.headers.get("location", "")
                    if dest and dest != url:
                        return dest
                
                # Second form submit might be needed
                soup2 = BeautifulSoup(resp2.text, "html.parser")
                form2 = soup2.find("form", {"method": "POST"})
                if form2:
                    action2 = form2.get("action", "")
                    data2 = {}
                    for inp in form2.find_all("input"):
                        name = inp.get("name")
                        if name:
                            data2[name] = inp.get("value", "")
                    resp3 = await client.post(action2, data=data2, follow_redirects=False)
                    if resp3.status_code in (301, 302):
                        dest = resp3.headers.get("location", "")
                        if dest:
                            return dest
    except Exception:
        pass
    return None

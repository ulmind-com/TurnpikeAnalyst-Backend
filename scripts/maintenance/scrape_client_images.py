import requests
from bs4 import BeautifulSoup
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
}
res = requests.get("https://www.turnpikeanalyst.com/our_clients__partners/", headers=headers)
soup = BeautifulSoup(res.text, 'html.parser')

data = []
current_cat = None

for el in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'img']):
    if el.name.startswith('h'):
        text = el.text.strip()
        if text and text.lower() not in ['turnpikeanalyst', 'our clients & partners', 'contact info', 'newsletter']:
            current_cat = text
            data.append({"category": current_cat, "clients": []})
    elif el.name == 'img' and current_cat:
        alt = el.get('alt', '').strip()
        src = el.get('src', '').strip()
        
        # some images might not be clients (like icons in footer), let's just grab ones that have src
        if src and "logo" not in src.lower() and "icon" not in src.lower() and "banner" not in src.lower():
            if not src.startswith('http'):
                src = 'https://www.turnpikeanalyst.com' + src if src.startswith('/') else 'https://www.turnpikeanalyst.com/' + src
            # only add if alt has "removebg" or it's a known client
            if "removebg" in alt.lower() or "united" in alt.lower() or "era" in alt.lower() or "3m" in alt.lower() or "bd" in alt.lower():
                data[-1]["clients"].append({
                    "alt": alt,
                    "src": src
                })
        elif src and "removebg" in src.lower():
            if not src.startswith('http'):
                src = 'https://www.turnpikeanalyst.com' + src if src.startswith('/') else 'https://www.turnpikeanalyst.com/' + src
            data[-1]["clients"].append({
                "alt": alt,
                "src": src
            })

print(json.dumps(data, indent=2))

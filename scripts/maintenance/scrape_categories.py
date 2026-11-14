import requests
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
}
res = requests.get("https://www.turnpikeanalyst.com/our_clients__partners/", headers=headers)
soup = BeautifulSoup(res.text, 'html.parser')

print("--- SITE STRUCTURE ---")
for el in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'img']):
    if el.name.startswith('h'):
        print(f"\nHEADER: {el.text.strip()}")
    elif el.name == 'img':
        alt = el.get('alt', '').strip()
        if alt:
            print(f"IMG: {alt}")

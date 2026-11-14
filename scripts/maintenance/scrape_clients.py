import requests
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Accept': 'text/html'
}
res = requests.get("https://www.turnpikeanalyst.com/our_clients__partners/", headers=headers)
print("Status:", res.status_code)
if res.status_code == 200:
    soup = BeautifulSoup(res.text, 'html.parser')
    imgs = soup.find_all('img')
    for img in imgs:
        alt = img.get('alt', '').strip()
        if alt:
            print("ALT:", alt)
    
    print("\n--- TEXT SNIPPETS ---")
    for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'div', 'span']):
        cls = heading.get('class', [])
        if any('client' in str(c).lower() or 'partner' in str(c).lower() for c in cls):
            print(heading.text.strip())

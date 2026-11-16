import requests
from bs4 import BeautifulSoup

for page in [2, 3]:
    print(f'\nPage {page}:')
    res = requests.get(f'https://www.turnpikeanalyst.com/blog-posts/page/{page}/')
    soup = BeautifulSoup(res.text, 'html.parser')
    for a in soup.find_all('a', class_='tpg-post-title') or soup.select('.rt-title a') or soup.select('h3 a'):
        print(a.get('href'), a.text.strip())

import urllib.request
from bs4 import BeautifulSoup

def fetch_soup(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
    res = urllib.request.urlopen(req)
    return BeautifulSoup(res.read().decode('utf-8'), 'html.parser')

def main():
    try:
        print("Scraping FAQ...")
        faq_soup = fetch_soup("https://www.turnpikeanalyst.com/faq/")
        faq_text = faq_soup.get_text(separator='\n', strip=True)
        
        print("Scraping Career...")
        career_soup = fetch_soup("https://www.turnpikeanalyst.com/career/")
        career_text = career_soup.get_text(separator='\n', strip=True)
        
        print("Scraping Clients...")
        clients_soup = fetch_soup("https://www.turnpikeanalyst.com/our_clients__partners/")
        clients_text = clients_soup.get_text(separator='\n', strip=True)
        
        with open('scraped_temp.txt', 'w', encoding='utf-8') as f:
            f.write("=== FAQ ===\n" + faq_text[:2000] + "\n=== CAREER ===\n" + career_text[:2000] + "\n=== CLIENTS ===\n" + clients_text[:2000])
        print("Done writing to scraped_temp.txt")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()

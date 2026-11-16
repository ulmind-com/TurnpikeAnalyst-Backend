import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
import os
import time
# Connection details come from configuration, never hardcoded: these are
# one-off maintenance scripts and they live in a public repository.
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.core.config import settings

MONGO_URL = settings.MONGODB_URL

urls = {
    "applications": "https://www.turnpikeanalyst.com/applications/",
    "artificial-augmented-intelligence": "https://www.turnpikeanalyst.com/artificial-augmented-intelligence/",
    "business-process": "https://www.turnpikeanalyst.com/business-process/",
    "business-solutions": "https://www.turnpikeanalyst.com/business-solutions/",
    "cloud": "https://www.turnpikeanalyst.com/cloud/",
    "consulting": "https://www.turnpikeanalyst.com/consulting/",
    "cybersecurity": "https://www.turnpikeanalyst.com/cybersecurity/",
    "data-analytics": "https://www.turnpikeanalyst.com/data-analytics/",
    "design-experience": "https://www.turnpikeanalyst.com/design-experience/",
    "digital-marketing-interaction": "https://www.turnpikeanalyst.com/digital-marketing-interaction/",
    "engineering": "https://www.turnpikeanalyst.com/engineering/",
    "infrastructure": "https://www.turnpikeanalyst.com/infrastructure/",
    "sustainability": "https://www.turnpikeanalyst.com/sustainability/",
    "talent-cloud": "https://www.turnpikeanalyst.com/talent-cloud/",
    
    "aerospace-defense": "https://www.turnpikeanalyst.com/aerospace-defense/",
    "automotive": "https://www.turnpikeanalyst.com/automotive/",
    "banking": "https://www.turnpikeanalyst.com/banking/",
    "communications": "https://www.turnpikeanalyst.com/communications/",
    "consumer-electronics": "https://www.turnpikeanalyst.com/consumer-electronics/",
    "consumer-packaged-goods": "https://www.turnpikeanalyst.com/consumer-packaged-goods/",
    "education": "https://www.turnpikeanalyst.com/education/",
    "engineering-construction-operations": "https://www.turnpikeanalyst.com/engineering-construction-operations/",
    "healthcare": "https://www.turnpikeanalyst.com/healthcare/",
    "industrial-process-manufacturing": "https://www.turnpikeanalyst.com/industrial-process-manufacturing/",
    "insurance": "https://www.turnpikeanalyst.com/insurance/",
    "life-sciences-pharma": "https://www.turnpikeanalyst.com/life-sciences-pharma/",
    "media-info-services": "https://www.turnpikeanalyst.com/media-info-services/",
    "medical-devices": "https://www.turnpikeanalyst.com/medical-devices/",
    "natural-resources": "https://www.turnpikeanalyst.com/natural-resources/",
    "oil-gas": "https://www.turnpikeanalyst.com/oil-gas/",
    "platforms-software-products": "https://www.turnpikeanalyst.com/platforms-software-products/",
    "professional-services": "https://www.turnpikeanalyst.com/professional-services/",
    "public-sector": "https://www.turnpikeanalyst.com/public-sector/",
    "retail": "https://www.turnpikeanalyst.com/retail/",
    "semiconductors": "https://www.turnpikeanalyst.com/semiconductors/",
    "transportation-services": "https://www.turnpikeanalyst.com/transportation-services/",
    "utilities": "https://www.turnpikeanalyst.com/utilities/",
    
    "digital-content-migration-2": "http://www.turnpikeanalyst.com/digital-content-migration-2/",
    "digital-content-migration": "http://www.turnpikeanalyst.com/digital-content-migration/",
    "managed-services": "http://www.turnpikeanalyst.com/managed-services/",
    
    "software-support": "https://www.turnpikeanalyst.com/software-support/",
    "our_clients__partners": "http://www.turnpikeanalyst.com/our_clients__partners/",
    "faq": "http://www.turnpikeanalyst.com/faq/",
    "career": "https://www.turnpikeanalyst.com/career/"
}

try:
    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    db = client.turnpike_analyst
    services_collection = db.services
    
    # Optional: Clear existing to ensure clean state
    # services_collection.delete_many({})

    headers = {'User-Agent': 'Mozilla/5.0'}
    
    count = 0
    for slug, url in urls.items():
        print(f"Scraping: {url} ...")
        try:
            title = slug.replace('-', ' ').title()
            combined_text = ''
            
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                
                title_tag = soup.find('h1')
                if title_tag:
                    title = title_tag.text.strip()
                
                paragraphs = soup.find_all(['p', 'h2', 'h3'])
                full_text = []
                for p in paragraphs:
                    text = p.text.strip()
                    if text and len(text) > 20: 
                        full_text.append(text)
                
                combined_text = "\n\n".join(full_text)
                
            if not combined_text:
                combined_text = f"We provide industry-leading solutions for {title}. Our expert teams are dedicated to accelerating your digital transformation with state of the art engineering and strategic consulting."
                
            short_desc = combined_text[:180] + "..." if len(combined_text) > 180 else combined_text
            
            category = "services"
            if "digital-content" in slug or "managed-services" in slug:
                category = "digital content services"
            elif slug in ["applications", "cloud", "cybersecurity", "engineering"]:
                category = "services"
            else:
                category = "industries" 

            service_doc = {
                "title": title,
                "slug": slug,
                "short_description": short_desc,
                "full_description": combined_text,
                "parent_category": category,
                "sub_service_type": "Core Offering",
                "supported_platforms": ["Web", "Mobile", "Cloud Infrastructure", "Enterprise"]
            }
            
            services_collection.update_one({"slug": slug}, {"$set": service_doc}, upsert=True)
            count += 1
                
        except Exception as e:
            print(f"Failed to scrape {url}: {e}")
            
        time.sleep(0.5) # Avoid hitting their servers too hard

    print(f"Successfully scraped and injected {count} pages into MongoDB!")

except Exception as ex:
    print(f"Database Error: {ex}")

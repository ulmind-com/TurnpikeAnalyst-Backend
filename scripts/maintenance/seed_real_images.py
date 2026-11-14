import asyncio
import logging
from app.db.mongodb import db_client, get_db
from app.crud.content import get_client_categories, update_client_category

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_real_images")

# The exact data scraped from the live site
real_data = [
  {
    "category": "Technology & Communication",
    "clients": [
      {
        "name": "Agilent",
        "img": "https://www.turnpikeanalyst.com/wp-content/uploads/2024/08/aglient-removebg-preview.png"
      },
      {
        "name": "Infor",
        "img": "https://www.turnpikeanalyst.com/wp-content/uploads/2024/08/infor-removebg-preview.png"
      },
      {
        "name": "Telekom",
        "img": "https://www.turnpikeanalyst.com/wp-content/uploads/2024/08/telekom-removebg-preview.png"
      },
      {
        "name": "ABB",
        "img": "https://www.turnpikeanalyst.com/wp-content/uploads/2024/08/ABB-removebg-preview.png"
      }
    ]
  },
  {
    "category": "Insurance",
    "clients": [
      {
        "name": "Security",
        "img": "https://www.turnpikeanalyst.com/wp-content/uploads/2024/08/security-removebg-preview.png"
      },
      {
        "name": "Kaiser",
        "img": "https://www.turnpikeanalyst.com/wp-content/uploads/2024/08/keiser-removebg-preview.png"
      },
      {
        "name": "American National",
        "img": "https://www.turnpikeanalyst.com/wp-content/uploads/2024/08/American_National-removebg-preview.png"
      }
    ]
  },
  {
    "category": "Financial Services",
    "clients": [
      {
        "name": "Security America",
        "img": "https://www.turnpikeanalyst.com/wp-content/uploads/2024/08/secrity_americaa-removebg-preview.png"
      },
      {
        "name": "KeyBank",
        "img": "https://www.turnpikeanalyst.com/wp-content/uploads/2024/08/key_bank-removebg-preview.png"
      },
      {
        "name": "Flaster",
        "img": "https://www.turnpikeanalyst.com/wp-content/uploads/2024/08/flaster-removebg-preview.png"
      },
      {
        "name": "Citi",
        "img": "https://www.turnpikeanalyst.com/wp-content/uploads/2024/08/city-removebg-preview.png"
      },
      {
        "name": "Savings Bank",
        "img": "https://www.turnpikeanalyst.com/wp-content/uploads/2024/08/a_Savinf_b-removebg-preview.png"
      },
      {
        "name": "IBD",
        "img": "https://www.turnpikeanalyst.com/wp-content/uploads/2024/08/ibd-removebg-preview.png"
      }
    ]
  },
  {
    "category": "Distribution & Retail",
    "clients": [
      {
        "name": "BD",
        "img": "https://www.turnpikeanalyst.com/wp-content/uploads/2024/08/BD-removebg-preview.png"
      },
      {
        "name": "3M",
        "img": "https://www.turnpikeanalyst.com/wp-content/uploads/2024/08/3-removebg-preview.png"
      },
      {
        "name": "Plexus",
        "img": "https://www.turnpikeanalyst.com/wp-content/uploads/2024/08/plexus-removebg-preview.png"
      }
    ]
  },
  {
    "category": "Travel & Transportation",
    "clients": [
      {
        "name": "Truck",
        "img": "https://www.turnpikeanalyst.com/wp-content/uploads/2024/08/truck-removebg-preview.png"
      },
      {
        "name": "American Airlines",
        "img": "https://www.turnpikeanalyst.com/wp-content/uploads/2024/08/Amrican_Airline-removebg-preview.png"
      },
      {
        "name": "United Airlines",
        "img": "https://www.turnpikeanalyst.com/wp-content/uploads/2024/08/united_air-removebg-preview.png"
      },
      {
        "name": "ERA LLC",
        "img": "https://www.turnpikeanalyst.com/wp-content/uploads/2024/08/era_llc-removebg-preview.png"
      }
    ]
  }
]

async def seed():
    db_client.connect_db()
    db = get_db()
    
    cats = await get_client_categories(db, skip=0, limit=100)
    for cat in cats:
        cat_dict = cat.model_dump() if hasattr(cat, 'model_dump') else dict(cat)
        cat_name = cat_dict.get('category', '').lower()
        
        # Find the matching real data category
        real_cat = next((rc for rc in real_data if rc['category'].lower() == cat_name), None)
        if not real_cat:
            continue
            
        # We can just completely replace the clients array with the high-res one
        cat_id = cat.id if hasattr(cat, 'id') else cat_dict['_id']
        await update_client_category(db, str(cat_id), {"clients": real_cat['clients']})
        logger.info(f"Updated category {cat_dict.get('category')} with real high-res images.")

    db_client.close_db()

if __name__ == "__main__":
    asyncio.run(seed())

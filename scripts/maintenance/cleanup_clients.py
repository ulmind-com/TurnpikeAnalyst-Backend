import asyncio
import logging
from app.db.mongodb import db_client, get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cleanup_clients")

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
        "name": "Security Mutual Life",
        "img": "https://www.turnpikeanalyst.com/wp-content/uploads/2024/08/security-removebg-preview.png"
      },
      {
        "name": "Kaiser Permanente",
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
        "name": "Securities America",
        "img": "https://www.turnpikeanalyst.com/wp-content/uploads/2024/08/secrity_americaa-removebg-preview.png"
      },
      {
        "name": "KeyBank",
        "img": "https://www.turnpikeanalyst.com/wp-content/uploads/2024/08/key_bank-removebg-preview.png"
      },
      {
        "name": "Flagstar",
        "img": "https://www.turnpikeanalyst.com/wp-content/uploads/2024/08/flaster-removebg-preview.png"
      },
      {
        "name": "City National Bank",
        "img": "https://www.turnpikeanalyst.com/wp-content/uploads/2024/08/city-removebg-preview.png"
      },
      {
        "name": "American Savings Bank",
        "img": "https://www.turnpikeanalyst.com/wp-content/uploads/2024/08/a_Savinf_b-removebg-preview.png"
      },
      {
        "name": "IDBank",
        "img": "https://www.turnpikeanalyst.com/wp-content/uploads/2024/08/ibd-removebg-preview.png"
      }
    ]
  },
  {
    "category": "Distribution & Retail",
    "clients": [
      {
        "name": "Black+Decker",
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
        "name": "Southeastern Freight",
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

async def cleanup():
    db_client.connect_db()
    db = get_db()
    
    # 1. Delete all existing client categories
    result = await db.client_categories.delete_many({})
    logger.info(f"Deleted {result.deleted_count} old client categories.")
    
    # 2. Insert the correct ones
    for cat in real_data:
        cat_doc = {
            "category": cat["category"],
            "cols": 4,
            "clients": cat["clients"]
        }
        await db.client_categories.insert_one(cat_doc)
        logger.info(f"Inserted correct category: {cat['category']}")

    db_client.close_db()

if __name__ == "__main__":
    asyncio.run(cleanup())

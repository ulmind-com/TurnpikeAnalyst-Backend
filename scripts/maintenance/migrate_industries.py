import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
import re
# Connection details come from configuration, never hardcoded: these are
# one-off maintenance scripts and they live in a public repository.
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.core.config import settings

def slugify(s):
    s = s.lower().strip()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'[\s-]+', '-', s)
    return s

async def main():
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client.get_database("turnpike_analyst")
    
    # First clear out existing industries (which might be the old schema)
    await db.industries.delete_many({})
    
    categories = [
      {
        "name": "FINANCE & PROFESSIONAL",
        "items": [
          { "title": "Banking", "description": "Digital transformation" },
          { "title": "Insurance", "description": "Policy management" },
          { "title": "Professional Services", "description": "Consulting & advisory" },
          { "title": "Public Sector", "description": "Government solutions" },
          { "title": "Education", "description": "EdTech platforms" }
        ]
      },
      {
        "name": "HEALTH & LIFE SCIENCES",
        "items": [
          { "title": "Healthcare", "description": "Patient portals" },
          { "title": "Life Sciences & Pharma", "description": "Clinical trial data" },
          { "title": "Medical Devices", "description": "IoT & device management" }
        ]
      },
      {
        "name": "INDUSTRIAL & RESOURCES",
        "items": [
          { "title": "Industrial & Process Manufacturing", "description": "Supply chain ops" },
          { "title": "Engineering Construction & Operations", "description": "Project management" },
          { "title": "Natural Resources", "description": "Resource planning" },
          { "title": "Oil & Gas", "description": "Energy analytics" },
          { "title": "Utilities", "description": "Grid management" }
        ]
      },
      {
        "name": "CONSUMER & TRANSPORT",
        "items": [
          { "title": "Retail", "description": "E-commerce & omnichannel" },
          { "title": "Consumer Packaged Goods", "description": "Inventory & distribution" },
          { "title": "Consumer Electronics", "description": "Smart home integrations" },
          { "title": "Automotive", "description": "Connected vehicles" },
          { "title": "Aerospace & Defense", "description": "Secure comms" },
          { "title": "Transportation & Services", "description": "Logistics systems" },
          { "title": "Media & Info Services", "description": "Content delivery" },
          { "title": "Platforms & Software Products", "description": "SaaS architecture" },
          { "title": "Semiconductors", "description": "Supply chain analytics" }
        ]
      }
    ]
    
    for cat in categories:
        for item in cat["items"]:
            industry = {
                "title": item["title"],
                "slug": slugify(item["title"]),
                "parent_category": cat["name"],
                "short_description": item["description"],
                "full_description": f"{item['title']} solutions for modern enterprises.",
                "supported_platforms": ["Web", "Mobile"],
                "is_featured": False,
                "sections": [],
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            await db.industries.insert_one(industry)
            print(f"Inserted: {industry['title']}")

if __name__ == "__main__":
    asyncio.run(main())

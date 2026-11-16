import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
# Connection details come from configuration, never hardcoded: these are
# one-off maintenance scripts and they live in a public repository.
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.core.config import settings

async def main():
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client.get_database("turnpike_analyst")
    
    allowed_services = [
        "Applications",
        "Artificial & Augmented Intelligence",
        "Business Process",
        "Business Solutions",
        "Cloud",
        "Consulting",
        "Cybersecurity",
        "Data & Analytics",
        "Design & Experience",
        "Digital Marketing & Interaction",
        "Engineering",
        "Infrastructure",
        "Sustainability",
        "Talent Cloud"
    ]
    
    # delete those that are not in allowed list
    result = await db.services.delete_many({"title": {"$nin": allowed_services}})
    print(f"Deleted {result.deleted_count} unallowed services.")
    
    # check which ones are missing
    cursor = db.services.find({"title": {"$in": allowed_services}})
    existing_services = await cursor.to_list(length=100)
    existing_titles = [s["title"] for s in existing_services]
    
    missing_titles = [t for t in allowed_services if t not in existing_titles]
    print(f"Missing services: {missing_titles}")

asyncio.run(main())

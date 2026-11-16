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
    services = await db.services.find({}).to_list(100)
    for s in services:
        print(f"{s['title']} - {s.get('parent_category')} - {s.get('sub_service_type')}")

if __name__ == "__main__":
    asyncio.run(main())

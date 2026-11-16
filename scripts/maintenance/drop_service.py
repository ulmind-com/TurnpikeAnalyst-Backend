import asyncio
from app.db.mongodb import db_client, get_db

async def drop_service():
    db_client.connect_db()
    db = get_db()
    await db.services.delete_one({"slug": "filenet-to-cloud-migration"})
    print("Deleted filenet-to-cloud-migration service.")

if __name__ == "__main__":
    asyncio.run(drop_service())

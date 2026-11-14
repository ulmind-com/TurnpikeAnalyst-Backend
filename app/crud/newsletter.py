from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.schemas.newsletter import NewsletterSubscribe

async def ensure_newsletter_indexes(db: AsyncIOMotorDatabase):
    await db.newsletters.create_index("email", unique=True)

async def subscribe_newsletter(db: AsyncIOMotorDatabase, sub_in: NewsletterSubscribe) -> Dict[str, Any]:
    existing = await db.newsletters.find_one({"email": sub_in.email})
    if existing:
        if not existing.get("is_active", True):
            await db.newsletters.update_one({"_id": existing["_id"]}, {"$set": {"is_active": True}})
            existing["is_active"] = True
        return existing
    data = {
        "email": sub_in.email,
        "subscribed_at": datetime.now(timezone.utc),
        "is_active": True
    }
    result = await db.newsletters.insert_one(data)
    data["_id"] = result.inserted_id
    return data

async def get_subscribers(db: AsyncIOMotorDatabase, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    cursor = db.newsletters.find({"is_active": True}).sort("subscribed_at", -1).skip(skip).limit(limit)
    return await cursor.to_list(length=limit)

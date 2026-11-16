from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

async def create_industry(db: AsyncIOMotorDatabase, data: Any) -> Dict[str, Any]:
    doc = data.model_dump()
    now = datetime.now(timezone.utc)
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db.industries.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc

async def get_industries(db: AsyncIOMotorDatabase, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    cursor = db.industries.find().sort("title", 1).skip(skip).limit(limit)
    return [{**doc, "_id": str(doc["_id"])} async for doc in cursor]

async def get_industry_by_slug(db: AsyncIOMotorDatabase, slug: str) -> Optional[Dict[str, Any]]:
    doc = await db.industries.find_one({"slug": slug})
    if doc:
        return {**doc, "_id": str(doc["_id"])}
    return None

async def update_industry(db: AsyncIOMotorDatabase, industry_id: str, data: Any) -> Optional[Dict[str, Any]]:
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        doc = await db.industries.find_one({"_id": ObjectId(industry_id)})
        return {**doc, "_id": str(doc["_id"])} if doc else None

    update_data["updated_at"] = datetime.now(timezone.utc)
    
    result = await db.industries.find_one_and_update(
        {"_id": ObjectId(industry_id)},
        {"$set": update_data},
        return_document=True
    )
    if result:
        return {**result, "_id": str(result["_id"])}
    return None

async def delete_industry(db: AsyncIOMotorDatabase, industry_id: str) -> bool:
    result = await db.industries.delete_one({"_id": ObjectId(industry_id)})
    return result.deleted_count > 0

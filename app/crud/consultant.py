from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from app.schemas.consultant import ConsultantCreate, ConsultantUpdate
from typing import List
from datetime import datetime, timezone
import pymongo

async def ensure_consultant_indexes(db: AsyncIOMotorDatabase):
    await db.consultants.create_index([("name", pymongo.ASCENDING)])

async def get_consultants(db: AsyncIOMotorDatabase, active_only: bool = False, skip: int = 0, limit: int = 100) -> List[dict]:
    query = {"is_active": True} if active_only else {}
    cursor = db.consultants.find(query).sort("name", 1).skip(skip).limit(limit)
    return await cursor.to_list(length=limit)

async def create_consultant(db: AsyncIOMotorDatabase, consultant_in: ConsultantCreate) -> dict:
    consultant_dict = consultant_in.model_dump()
    consultant_dict["created_at"] = datetime.now(timezone.utc)
    consultant_dict["updated_at"] = datetime.now(timezone.utc)
    result = await db.consultants.insert_one(consultant_dict)
    return await db.consultants.find_one({"_id": result.inserted_id})

async def update_consultant(db: AsyncIOMotorDatabase, consultant_id: str, consultant_in: ConsultantUpdate) -> dict | None:
    update_data = consultant_in.model_dump(exclude_unset=True)
    if not update_data:
        return await db.consultants.find_one({"_id": ObjectId(consultant_id)})
    
    update_data["updated_at"] = datetime.now(timezone.utc)
    result = await db.consultants.update_one(
        {"_id": ObjectId(consultant_id)},
        {"$set": update_data}
    )
    if result.modified_count > 0:
        return await db.consultants.find_one({"_id": ObjectId(consultant_id)})
    return None

async def delete_consultant(db: AsyncIOMotorDatabase, consultant_id: str) -> bool:
    result = await db.consultants.delete_one({"_id": ObjectId(consultant_id)})
    return result.deleted_count > 0

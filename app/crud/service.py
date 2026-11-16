from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.schemas.service import ServiceCreate, ServiceUpdate
from app.models.enums import ParentCategory, SubServiceType

async def ensure_service_indexes(db: AsyncIOMotorDatabase):
    await db.services.create_index("slug", unique=True)

async def get_services(
    db: AsyncIOMotorDatabase,
    parent_category: Optional[str] = None,
    sub_service_type: Optional[str] = None,
    exclude_category: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[Dict[str, Any]]:
    query = {}
    if parent_category:
        query["parent_category"] = parent_category
    if sub_service_type:
        query["sub_service_type"] = sub_service_type
    if exclude_category:
        query["parent_category"] = {"$ne": exclude_category}
    cursor = db.services.find(query).skip(skip).limit(limit)
    return await cursor.to_list(length=limit)

async def get_service_by_slug(db: AsyncIOMotorDatabase, slug: str) -> Optional[Dict[str, Any]]:
    return await db.services.find_one({"slug": slug})

async def get_service_by_id(db: AsyncIOMotorDatabase, service_id: str) -> Optional[Dict[str, Any]]:
    if not ObjectId.is_valid(service_id):
        return None
    return await db.services.find_one({"_id": ObjectId(service_id)})

async def create_service(db: AsyncIOMotorDatabase, service_in: ServiceCreate) -> Dict[str, Any]:
    service_dict = service_in.model_dump()
    service_dict["parent_category"] = service_in.parent_category
    service_dict["sub_service_type"] = service_in.sub_service_type
    service_dict["created_at"] = datetime.now(timezone.utc)
    result = await db.services.insert_one(service_dict)
    service_dict["_id"] = result.inserted_id
    return service_dict

async def update_service(db: AsyncIOMotorDatabase, service_id: str, service_in: ServiceUpdate) -> Optional[Dict[str, Any]]:
    if not ObjectId.is_valid(service_id):
        return None
    update_data = service_in.model_dump(exclude_unset=True)
    # Enum strings are directly written to db now without needing .value extraction
    
    if update_data:
        await db.services.update_one({"_id": ObjectId(service_id)}, {"$set": update_data})
    return await get_service_by_id(db, service_id)

async def delete_service(db: AsyncIOMotorDatabase, service_id: str) -> bool:
    if not ObjectId.is_valid(service_id):
        return False
    result = await db.services.delete_one({"_id": ObjectId(service_id)})
    return result.deleted_count > 0

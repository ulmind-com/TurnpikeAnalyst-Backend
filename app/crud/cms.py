from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.schemas.cms import AssetCreate

async def ensure_cms_indexes(db: AsyncIOMotorDatabase):
    await db.cms_assets.create_index("created_at")

async def create_asset(db: AsyncIOMotorDatabase, asset_in: AssetCreate) -> Dict[str, Any]:
    asset_dict = asset_in.model_dump()
    asset_dict["created_at"] = datetime.now(timezone.utc)
    result = await db.cms_assets.insert_one(asset_dict)
    asset_dict["_id"] = result.inserted_id
    return asset_dict

async def get_assets(db: AsyncIOMotorDatabase, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    cursor = db.cms_assets.find({}).sort("created_at", -1).skip(skip).limit(limit)
    return await cursor.to_list(length=limit)

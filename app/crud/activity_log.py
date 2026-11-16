from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.schemas.activity_log import ActivityLogCreate

async def ensure_activity_log_indexes(db: AsyncIOMotorDatabase):
    await db.activity_logs.create_index("created_at")
    await db.activity_logs.create_index("user_id")

async def create_activity_log(db: AsyncIOMotorDatabase, log_in: ActivityLogCreate) -> Dict[str, Any]:
    log_dict = log_in.model_dump()
    log_dict["created_at"] = datetime.now(timezone.utc)
    result = await db.activity_logs.insert_one(log_dict)
    log_dict["_id"] = result.inserted_id
    return log_dict

async def get_activity_logs(db: AsyncIOMotorDatabase, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    cursor = db.activity_logs.find({}).sort("created_at", -1).skip(skip).limit(limit)
    return await cursor.to_list(length=limit)

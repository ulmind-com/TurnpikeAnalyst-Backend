from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.schemas.lead import BookCallCreate, SubmitNeedsCreate, LeadStatusUpdate
from app.models.enums import LeadType, LeadStatus

async def ensure_lead_indexes(db: AsyncIOMotorDatabase):
    await db.appointments_and_leads.create_index("status")
    await db.appointments_and_leads.create_index("created_at")

async def create_book_call(db: AsyncIOMotorDatabase, book_in: BookCallCreate) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    data = book_in.model_dump()
    data["department"] = book_in.department.value
    data["type"] = LeadType.BOOK_CALL.value
    data["status"] = LeadStatus.PENDING.value
    if data.get("service_id") and ObjectId.is_valid(str(data["service_id"])):
        data["service_id"] = ObjectId(str(data["service_id"]))
    else:
        data["service_id"] = None
    data["created_at"] = now
    data["sla_reply_deadline"] = now + timedelta(hours=8)
    result = await db.appointments_and_leads.insert_one(data)
    data["_id"] = result.inserted_id
    return data

async def create_requirement_form(db: AsyncIOMotorDatabase, req_in: SubmitNeedsCreate) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    data = req_in.model_dump()
    data["department"] = req_in.department.value
    data["type"] = LeadType.REQUIREMENT_FORM.value
    data["status"] = LeadStatus.PENDING.value
    if data.get("service_id") and ObjectId.is_valid(str(data["service_id"])):
        data["service_id"] = ObjectId(str(data["service_id"]))
    else:
        data["service_id"] = None
    data["created_at"] = now
    data["sla_reply_deadline"] = now + timedelta(hours=8)
    result = await db.appointments_and_leads.insert_one(data)
    data["_id"] = result.inserted_id
    return data

async def get_leads(db: AsyncIOMotorDatabase, status: Optional[LeadStatus] = None, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    query = {}
    if status:
        query["status"] = status.value
    cursor = db.appointments_and_leads.find(query).sort("created_at", -1).skip(skip).limit(limit)
    return await cursor.to_list(length=limit)

async def update_lead_status(db: AsyncIOMotorDatabase, lead_id: str, update_in: LeadStatusUpdate) -> Optional[Dict[str, Any]]:
    if not ObjectId.is_valid(lead_id):
        return None
    await db.appointments_and_leads.update_one(
        {"_id": ObjectId(lead_id)},
        {"$set": {"status": update_in.status.value}}
    )
    return await db.appointments_and_leads.find_one({"_id": ObjectId(lead_id)})

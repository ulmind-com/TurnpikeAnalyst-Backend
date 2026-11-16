from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List

from app.db.mongodb import get_db
from app.schemas.activity_log import ActivityLogResponse
from app.crud.activity_log import get_activity_logs
from app.api.deps import get_current_active_user, require_roles
from app.models.enums import UserRole

router = APIRouter()

@router.get("/", response_model=List[ActivityLogResponse])
async def read_activity_logs(skip: int = 0, limit: int = 100, db: AsyncIOMotorDatabase = Depends(get_db), current_user: dict = Depends(require_roles([UserRole.ADMIN.value]))):
    logs = await get_activity_logs(db, skip=skip, limit=limit)
    return logs

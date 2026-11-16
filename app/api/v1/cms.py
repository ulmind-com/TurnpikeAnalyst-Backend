from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List

from app.db.mongodb import get_db
from app.schemas.cms import AssetResponse
from app.crud.cms import get_assets
from app.api.deps import get_current_active_user, require_roles
from app.models.enums import UserRole

router = APIRouter()

@router.get("/assets", response_model=List[AssetResponse])
async def read_assets(skip: int = 0, limit: int = 100, db: AsyncIOMotorDatabase = Depends(get_db), current_user: dict = Depends(require_roles([UserRole.ADMIN.value, UserRole.CONSULTANT.value]))):
    assets = await get_assets(db, skip=skip, limit=limit)
    return assets

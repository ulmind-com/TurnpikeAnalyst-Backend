from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.mongodb import get_db
from app.schemas.consultant import ConsultantCreate, ConsultantUpdate, ConsultantResponse
from app.crud.consultant import get_consultants, create_consultant, update_consultant, delete_consultant
from app.api.deps import require_roles
from app.models.enums import UserRole

router = APIRouter()

@router.get("/", response_model=List[ConsultantResponse])
async def read_consultants(
    active_only: bool = Query(True, description="Only return active consultants"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=10000),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Retrieve all consultants. This is a public endpoint used by the landing page.
    """
    return await get_consultants(db, active_only=active_only, skip=skip, limit=limit)

@router.post("/", response_model=ConsultantResponse, status_code=status.HTTP_201_CREATED)
async def create_new_consultant(
    consultant_in: ConsultantCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(require_roles([UserRole.ADMIN.value]))
):
    """
    Create a new consultant. Admin only.
    """
    return await create_consultant(db, consultant_in)

@router.put("/{consultant_id}", response_model=ConsultantResponse)
async def update_existing_consultant(
    consultant_id: str,
    consultant_in: ConsultantUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(require_roles([UserRole.ADMIN.value]))
):
    """
    Update an existing consultant. Admin only.
    """
    updated = await update_consultant(db, consultant_id, consultant_in)
    if not updated:
        raise HTTPException(status_code=404, detail="Consultant not found")
    return updated

@router.delete("/{consultant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_consultant(
    consultant_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(require_roles([UserRole.ADMIN.value]))
):
    """
    Delete a consultant. Admin only.
    """
    success = await delete_consultant(db, consultant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Consultant not found")
    return None

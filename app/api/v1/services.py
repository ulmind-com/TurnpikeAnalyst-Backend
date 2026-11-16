from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.mongodb import get_db
from app.schemas.service import ServiceCreate, ServiceUpdate, ServiceResponse
from app.schemas.common import MessageResponse
from app.models.enums import ParentCategory, SubServiceType
from app.crud.service import get_services, get_service_by_slug, create_service, update_service, delete_service
from app.api.deps import get_current_admin

router = APIRouter()

@router.get("/", response_model=List[ServiceResponse])
async def list_services(
    parent_category: Optional[str] = Query(None, description="Filter by parent category"),
    sub_service_type: Optional[str] = Query(None, description="Filter by sub-service type"),
    exclude_category: Optional[str] = Query(None, description="Exclude a specific parent category"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=10000),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    services = await get_services(db, parent_category=parent_category, sub_service_type=sub_service_type, exclude_category=exclude_category, skip=skip, limit=limit)
    return services

@router.get("/{slug}", response_model=ServiceResponse)
async def get_service(slug: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    service = await get_service_by_slug(db, slug)
    if not service:
        raise HTTPException(status_code=404, detail=f"Service with slug '{slug}' not found.")
    return service

@router.post("/", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
async def create_new_service(
    service_in: ServiceCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    existing = await get_service_by_slug(db, service_in.slug)
    if existing:
        raise HTTPException(status_code=400, detail="Service with this slug already exists.")
    created = await create_service(db, service_in)
    return created

@router.put("/{service_id}", response_model=ServiceResponse)
async def update_existing_service(
    service_id: str,
    service_in: ServiceUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    updated = await update_service(db, service_id, service_in)
    if not updated:
        raise HTTPException(status_code=404, detail="Service not found or invalid ID.")
    return updated

@router.delete("/{service_id}", response_model=MessageResponse)
async def delete_existing_service(
    service_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    success = await delete_service(db, service_id)
    if not success:
        raise HTTPException(status_code=404, detail="Service not found or could not be deleted.")
    return {"message": "Service successfully deleted."}

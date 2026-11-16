from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.mongodb import get_db
from app.schemas.lead import BookCallCreate, SubmitNeedsCreate, LeadResponse, LeadStatusUpdate
from app.models.enums import LeadStatus
from app.api.deps import require_roles
from app.models.enums import UserRole
from app.crud.lead import create_book_call, create_requirement_form, get_leads, update_lead_status

router = APIRouter()

@router.post("/book-call", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def book_call_appointment(book_in: BookCallCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
    lead = await create_book_call(db, book_in)
    return lead

@router.post("/submit-needs", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def submit_enterprise_requirements(req_in: SubmitNeedsCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
    lead = await create_requirement_form(db, req_in)
    return lead

@router.get("/", response_model=List[LeadResponse])
async def list_enterprise_leads(
    status_filter: Optional[LeadStatus] = Query(None, alias="status", description="Filter by lead status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=10000),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(require_roles([UserRole.ADMIN.value, UserRole.CONSULTANT.value]))
):
    leads = await get_leads(db, status=status_filter, skip=skip, limit=limit)
    return leads

@router.patch("/{lead_id}/status", response_model=LeadResponse)
async def patch_lead_status(
    lead_id: str,
    status_in: LeadStatusUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(require_roles([UserRole.ADMIN.value, UserRole.CONSULTANT.value]))
):
    updated = await update_lead_status(db, lead_id, status_in)
    if not updated:
        raise HTTPException(status_code=404, detail="Lead appointment not found or invalid ID.")
    return updated

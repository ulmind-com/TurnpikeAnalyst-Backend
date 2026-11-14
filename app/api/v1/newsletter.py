from typing import List
from fastapi import APIRouter, Depends, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.mongodb import get_db
from app.schemas.newsletter import NewsletterSubscribe, NewsletterResponse
from app.crud.newsletter import subscribe_newsletter, get_subscribers
from app.api.deps import require_roles
from app.models.enums import UserRole

router = APIRouter()

@router.post("/subscribe", response_model=NewsletterResponse, status_code=status.HTTP_201_CREATED)
async def subscribe_to_newsletter(sub_in: NewsletterSubscribe, db: AsyncIOMotorDatabase = Depends(get_db)):
    subscriber = await subscribe_newsletter(db, sub_in)
    return subscriber

@router.get("/subscribers", response_model=List[NewsletterResponse])
async def list_newsletter_subscribers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=10000),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(require_roles([UserRole.ADMIN.value, UserRole.CONSULTANT.value]))
):
    subscribers = await get_subscribers(db, skip=skip, limit=limit)
    return subscribers

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.mongodb import get_db
from app.schemas.blog import BlogCreate, BlogResponse
from app.models.enums import BlogCategory
from app.crud.blog import get_blogs, get_blog_by_slug, create_blog
from app.api.deps import get_current_admin

router = APIRouter()

@router.get("/", response_model=List[BlogResponse])
async def list_articles(
    category: Optional[BlogCategory] = Query(None, description="Filter by blog category"),
    tag: Optional[str] = Query(None, description="Filter by specific keyword tag"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=10000),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    articles = await get_blogs(db, category=category, tag=tag, skip=skip, limit=limit)
    return articles

@router.get("/{slug}", response_model=BlogResponse)
async def get_article_detail(slug: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    article = await get_blog_by_slug(db, slug)
    if not article:
        raise HTTPException(status_code=404, detail=f"Article with slug '{slug}' not found.")
    return article

@router.post("/", response_model=BlogResponse, status_code=status.HTTP_201_CREATED)
async def publish_article(
    blog_in: BlogCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    existing = await get_blog_by_slug(db, blog_in.slug)
    if existing:
        raise HTTPException(status_code=400, detail="Article with this slug already exists.")
    created = await create_blog(db, blog_in)
    return created

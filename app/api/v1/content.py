from typing import List
from fastapi import APIRouter, Depends, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.mongodb import get_db
from app.schemas.content import (
    TestimonialCreate, TestimonialResponse, 
    AwardCreate, AwardResponse, 
    StatCreate, StatResponse,
    ClientCategoryCreate, ClientCategoryResponse,
    BlogPostCreate, BlogPostResponse,
    ClientIndustryCreate, ClientIndustryResponse
)
from app.schemas.industry import IndustryCreate, IndustryResponse, IndustryUpdate
import app.crud.industry as industry_crud
from app.crud.content import (
    create_testimonial, get_testimonials,
    create_award, get_awards,
    create_stat, get_stats,
    create_client_category, get_client_categories,
    create_blog, get_blogs, get_blog_by_slug,
    create_client_industry, get_client_industries, delete_client_industry
)
from app.api.deps import get_current_admin
from fastapi import HTTPException

router = APIRouter()

# Client Industries
@router.post("/client-industries", response_model=ClientIndustryResponse, status_code=status.HTTP_201_CREATED)
async def add_client_industry(data_in: ClientIndustryCreate, db: AsyncIOMotorDatabase = Depends(get_db), current_admin: dict = Depends(get_current_admin)):
    return await create_client_industry(db, data_in)

@router.get("/client-industries", response_model=List[ClientIndustryResponse])
async def list_client_industries(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=10000), db: AsyncIOMotorDatabase = Depends(get_db)):
    return await get_client_industries(db, skip=skip, limit=limit)

@router.delete("/client-industries/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_client_industry(item_id: str, db: AsyncIOMotorDatabase = Depends(get_db), current_admin: dict = Depends(get_current_admin)):
    await delete_client_industry(db, item_id)
    return None

# Testimonials
@router.post("/testimonials", response_model=TestimonialResponse, status_code=status.HTTP_201_CREATED)
async def add_testimonial(data_in: TestimonialCreate, db: AsyncIOMotorDatabase = Depends(get_db), current_admin: dict = Depends(get_current_admin)):
    result = await create_testimonial(db, data_in)
    return result

@router.get("/testimonials", response_model=List[TestimonialResponse])
async def list_testimonials(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=10000), db: AsyncIOMotorDatabase = Depends(get_db)):
    return await get_testimonials(db, skip=skip, limit=limit)

# Awards
@router.post("/awards", response_model=AwardResponse, status_code=status.HTTP_201_CREATED)
async def add_award(data_in: AwardCreate, db: AsyncIOMotorDatabase = Depends(get_db), current_admin: dict = Depends(get_current_admin)):
    result = await create_award(db, data_in)
    return result

@router.get("/awards", response_model=List[AwardResponse])
async def list_awards(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=10000), db: AsyncIOMotorDatabase = Depends(get_db)):
    return await get_awards(db, skip=skip, limit=limit)

# Stats
@router.post("/stats", response_model=StatResponse, status_code=status.HTTP_201_CREATED)
async def add_stat(data_in: StatCreate, db: AsyncIOMotorDatabase = Depends(get_db), current_admin: dict = Depends(get_current_admin)):
    result = await create_stat(db, data_in)
    return result

@router.get("/stats", response_model=List[StatResponse])
async def list_stats(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=10000), db: AsyncIOMotorDatabase = Depends(get_db)):
    return await get_stats(db, skip=skip, limit=limit)

# Client Categories
@router.post("/clients", response_model=ClientCategoryResponse, status_code=status.HTTP_201_CREATED)
async def add_client_category(data_in: ClientCategoryCreate, db: AsyncIOMotorDatabase = Depends(get_db), current_admin: dict = Depends(get_current_admin)):
    return await create_client_category(db, data_in)


@router.put("/clients/{id}", response_model=ClientCategoryResponse)
async def update_client_category_endpoint(id: str, data_in: ClientCategoryCreate, db: AsyncIOMotorDatabase = Depends(get_db), current_admin: dict = Depends(get_current_admin)):
    return await content_crud.update_client_category(db, id, data_in.dict())

@router.delete("/clients/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client_category_endpoint(id: str, db: AsyncIOMotorDatabase = Depends(get_db), current_admin: dict = Depends(get_current_admin)):
    await content_crud.delete_client_category(db, id)

@router.get("/clients", response_model=List[ClientCategoryResponse])
async def list_client_categories(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=10000), db: AsyncIOMotorDatabase = Depends(get_db)):
    return await get_client_categories(db, skip=skip, limit=limit)

# Industries
@router.post("/industries", response_model=IndustryResponse, status_code=status.HTTP_201_CREATED)
async def add_industry(data_in: IndustryCreate, db: AsyncIOMotorDatabase = Depends(get_db), current_admin: dict = Depends(get_current_admin)):
    return await industry_crud.create_industry(db, data_in)

@router.get("/industries", response_model=List[IndustryResponse])
async def list_industries(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=10000), db: AsyncIOMotorDatabase = Depends(get_db)):
    return await industry_crud.get_industries(db, skip=skip, limit=limit)

@router.get("/industries/{slug}", response_model=IndustryResponse)
async def get_industry(slug: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    industry = await industry_crud.get_industry_by_slug(db, slug)
    if not industry:
        raise HTTPException(status_code=404, detail="Industry not found")
    return industry

@router.put("/industries/{id}", response_model=IndustryResponse)
async def update_industry_endpoint(id: str, data_in: IndustryUpdate, db: AsyncIOMotorDatabase = Depends(get_db), current_admin: dict = Depends(get_current_admin)):
    updated = await industry_crud.update_industry(db, id, data_in)
    if not updated:
        raise HTTPException(status_code=404, detail="Industry not found")
    return updated

@router.delete("/industries/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_industry_endpoint(id: str, db: AsyncIOMotorDatabase = Depends(get_db), current_admin: dict = Depends(get_current_admin)):
    deleted = await industry_crud.delete_industry(db, id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Industry not found")

# Blogs
@router.post("/blogs", response_model=BlogPostResponse, status_code=status.HTTP_201_CREATED)
async def add_blog(data_in: BlogPostCreate, db: AsyncIOMotorDatabase = Depends(get_db), current_admin: dict = Depends(get_current_admin)):
    return await create_blog(db, data_in)
@router.get("/blogs/{slug}", response_model=BlogPostResponse)
async def get_blog(slug: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    blog = await get_blog_by_slug(db, slug)
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    return blog

@router.get("/blogs", response_model=List[BlogPostResponse])
async def list_blogs(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=10000), db: AsyncIOMotorDatabase = Depends(get_db)):
    return await get_blogs(db, skip=skip, limit=limit)

import app.schemas.content as content_schemas
from app.crud import content as content_crud

# FAQs
@router.post("/faqs", response_model=content_schemas.FaqResponse, status_code=status.HTTP_201_CREATED)
async def add_faq(data_in: content_schemas.FaqCreate, db: AsyncIOMotorDatabase = Depends(get_db), current_admin: dict = Depends(get_current_admin)):
    return await content_crud.create_faq(db, data_in)

@router.delete("/faqs/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_faq_endpoint(id: str, db: AsyncIOMotorDatabase = Depends(get_db), current_admin: dict = Depends(get_current_admin)):
    await content_crud.delete_faq(db, id)

@router.put("/faqs/{id}", response_model=content_schemas.FaqResponse)
async def update_faq_endpoint(id: str, data_in: content_schemas.FaqCreate, db: AsyncIOMotorDatabase = Depends(get_db), current_admin: dict = Depends(get_current_admin)):
    return await content_crud.update_faq(db, id, data_in.model_dump())



@router.get("/faqs", response_model=List[content_schemas.FaqResponse])
async def list_faqs(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=10000), db: AsyncIOMotorDatabase = Depends(get_db)):
    return await content_crud.get_faqs(db, skip=skip, limit=limit)

# Jobs
@router.post("/jobs", response_model=content_schemas.JobResponse, status_code=status.HTTP_201_CREATED)
async def add_job(data_in: content_schemas.JobCreate, db: AsyncIOMotorDatabase = Depends(get_db), current_admin: dict = Depends(get_current_admin)):
    return await content_crud.create_job(db, data_in)

@router.delete("/jobs/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job_endpoint(id: str, db: AsyncIOMotorDatabase = Depends(get_db), current_admin: dict = Depends(get_current_admin)):
    await content_crud.delete_job(db, id)

@router.get("/jobs", response_model=List[content_schemas.JobResponse])
async def list_jobs(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=10000), db: AsyncIOMotorDatabase = Depends(get_db)):
    return await content_crud.get_jobs(db, skip=skip, limit=limit)


# ───────────────────────── Homepage CMS (singleton) ─────────────────────────
import re
import uuid
from pathlib import Path

from fastapi import UploadFile, File
from app.schemas.homepage import HomepageContent, HomepageUpdate, ImageUploadResponse
from app.crud.homepage import get_homepage, set_homepage
from app.services.storage import store, StorageError

_ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/svg+xml", "image/gif"}
_MAX_IMAGE_BYTES = 10 * 1024 * 1024


@router.get("/homepage", response_model=HomepageContent)
async def read_homepage(db: AsyncIOMotorDatabase = Depends(get_db)):
    """Public: the full editable homepage content, defaults filling any gaps."""
    return await get_homepage(db)


@router.put("/homepage", response_model=HomepageContent)
async def update_homepage(
    data_in: HomepageUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    """Admin: replace the homepage content document wholesale."""
    return await set_homepage(db, data_in)


@router.post("/homepage/upload-image", response_model=ImageUploadResponse)
async def upload_homepage_image(
    file: UploadFile = File(...),
    _: dict = Depends(get_current_admin),
):
    """Admin: upload a card/section image for the homepage and return its URL."""
    if file.content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="Image must be PNG, JPEG, WebP, GIF or SVG.")
    payload = await file.read()
    if len(payload) > _MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image must be 10 MB or smaller.")
    suffix = Path(file.filename or "").suffix.lower()
    if not re.fullmatch(r"\.(png|jpe?g|webp|gif|svg)", suffix):
        suffix = ".png"
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    try:
        stored = await store(payload, folder="homepage", filename=stored_name, private=False)
    except StorageError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"url": stored.url or f"/uploads/homepage/{stored_name}", "key": stored.key}

from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.schemas.content import TestimonialCreate, AwardCreate, StatCreate

async def ensure_content_indexes(db: AsyncIOMotorDatabase):
    pass  # No unique indexes required for these yet

# Testimonials
async def create_testimonial(db: AsyncIOMotorDatabase, data: TestimonialCreate) -> Dict[str, Any]:
    doc = data.model_dump()
    result = await db.testimonials.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc

async def get_testimonials(db: AsyncIOMotorDatabase, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    cursor = db.testimonials.find().skip(skip).limit(limit)
    return [{**doc, "_id": str(doc["_id"])} async for doc in cursor]

# Awards
async def create_award(db: AsyncIOMotorDatabase, data: AwardCreate) -> Dict[str, Any]:
    doc = data.model_dump()
    result = await db.awards.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc

async def get_awards(db: AsyncIOMotorDatabase, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    cursor = db.awards.find().skip(skip).limit(limit)
    return [{**doc, "_id": str(doc["_id"])} async for doc in cursor]

# Stats
async def create_stat(db: AsyncIOMotorDatabase, data: StatCreate) -> Dict[str, Any]:
    doc = data.model_dump()
    result = await db.stats.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc

async def get_stats(db: AsyncIOMotorDatabase, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    cursor = db.stats.find().skip(skip).limit(limit)
    return [{**doc, "_id": str(doc["_id"])} async for doc in cursor]

# Client Categories
async def create_client_category(db: AsyncIOMotorDatabase, data: Any) -> Dict[str, Any]:
    doc = data.model_dump()
    result = await db.client_categories.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc

async def get_client_categories(db: AsyncIOMotorDatabase, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    cursor = db.client_categories.find().skip(skip).limit(limit)
    return [{**doc, "_id": str(doc["_id"])} async for doc in cursor]

# Client Industries
async def create_client_industry(db: AsyncIOMotorDatabase, data: Any) -> Dict[str, Any]:
    doc = data.model_dump()
    result = await db.client_industries.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc

async def get_client_industries(db: AsyncIOMotorDatabase, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    cursor = db.client_industries.find().skip(skip).limit(limit)
    return [{**doc, "_id": str(doc["_id"])} async for doc in cursor]

# Blogs
async def create_blog(db: AsyncIOMotorDatabase, data: Any) -> Dict[str, Any]:
    doc = data.model_dump()
    result = await db.blogs.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc

async def get_blogs(db: AsyncIOMotorDatabase, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    cursor = db.blogs.find().skip(skip).limit(limit)
    return [{**doc, "_id": str(doc["_id"])} async for doc in cursor]

async def get_blog_by_slug(db: AsyncIOMotorDatabase, slug: str) -> Optional[Dict[str, Any]]:
    doc = await db.blogs.find_one({"slug": slug})
    if doc:
        return {**doc, "_id": str(doc["_id"])}
    return None

# FAQs
async def create_faq(db: AsyncIOMotorDatabase, data: Any) -> Dict[str, Any]:
    doc = data.model_dump()
    result = await db.faqs.insert_one(doc)
    doc['_id'] = str(result.inserted_id)
    return doc

async def get_faqs(db: AsyncIOMotorDatabase, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    cursor = db.faqs.find().skip(skip).limit(limit)
    return [{**doc, '_id': str(doc['_id'])} async for doc in cursor]

# Jobs
async def create_job(db: AsyncIOMotorDatabase, data: Any) -> Dict[str, Any]:
    doc = data.model_dump()
    result = await db.jobs.insert_one(doc)
    doc['_id'] = str(result.inserted_id)
    return doc

async def get_jobs(db: AsyncIOMotorDatabase, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    cursor = db.jobs.find().skip(skip).limit(limit)
    return [{**doc, '_id': str(doc['_id'])} async for doc in cursor]

from bson import ObjectId

async def delete_client_industry(db, id: str):
    await db.client_industries.delete_one({"_id": ObjectId(id)})

async def delete_faq(db, id: str):
    await db.faqs.delete_one({"_id": ObjectId(id)})

async def update_faq(db, id: str, data: dict):
    await db.faqs.update_one({"_id": ObjectId(id)}, {"$set": data})
    result = await db.faqs.find_one({"_id": ObjectId(id)})
    if result:
        result["_id"] = str(result["_id"])
    return result

async def delete_job(db, id: str):
    await db.jobs.delete_one({"_id": ObjectId(id)})

async def update_client_category(db, id: str, data: dict):
    from bson import ObjectId
    await db.client_categories.update_one({"_id": ObjectId(id)}, {"$set": data})
    result = await db.client_categories.find_one({"_id": ObjectId(id)})
    if result:
        result["_id"] = str(result["_id"])
    return result

async def delete_client_category(db, id: str):
    from bson import ObjectId
    await db.client_categories.delete_one({"_id": ObjectId(id)})

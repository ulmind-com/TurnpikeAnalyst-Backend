from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.schemas.blog import BlogCreate
from app.models.enums import BlogCategory

async def ensure_blog_indexes(db: AsyncIOMotorDatabase):
    await db.blogs_and_articles.create_index("slug", unique=True)
    await db.blogs_and_articles.create_index("tags")

async def get_blogs(
    db: AsyncIOMotorDatabase,
    category: Optional[BlogCategory] = None,
    tag: Optional[str] = None,
    skip: int = 0,
    limit: int = 20
) -> List[Dict[str, Any]]:
    query = {"is_published": True}
    if category:
        query["category"] = category.value
    if tag:
        query["tags"] = tag
    cursor = db.blogs_and_articles.find(query).sort("published_at", -1).skip(skip).limit(limit)
    return await cursor.to_list(length=limit)

async def get_blog_by_slug(db: AsyncIOMotorDatabase, slug: str) -> Optional[Dict[str, Any]]:
    return await db.blogs_and_articles.find_one({"slug": slug, "is_published": True})

async def create_blog(db: AsyncIOMotorDatabase, blog_in: BlogCreate) -> Dict[str, Any]:
    data = blog_in.model_dump()
    data["category"] = blog_in.category.value
    data["published_at"] = datetime.now(timezone.utc)
    result = await db.blogs_and_articles.insert_one(data)
    data["_id"] = result.inserted_id
    return data

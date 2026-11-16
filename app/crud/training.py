from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.schemas.training import CourseCreate, CourseUpdate, InstructorApplicationCreate
from app.models.enums import CourseCategory, CourseLevel, ApplicationStatus

async def ensure_training_indexes(db: AsyncIOMotorDatabase):
    await db.courses_and_training.create_index("slug", unique=True)

async def get_published_courses(
    db: AsyncIOMotorDatabase,
    category: Optional[CourseCategory] = None,
    level: Optional[CourseLevel] = None,
    skip: int = 0,
    limit: int = 100
) -> List[Dict[str, Any]]:
    query = {"is_published": True}
    if category:
        query["category"] = category.value
    if level:
        query["level"] = level.value
    cursor = db.courses_and_training.find(query).skip(skip).limit(limit)
    return await cursor.to_list(length=limit)

async def get_course_by_slug(db: AsyncIOMotorDatabase, slug: str) -> Optional[Dict[str, Any]]:
    return await db.courses_and_training.find_one({"slug": slug, "is_published": True})

async def create_course(db: AsyncIOMotorDatabase, course_in: CourseCreate) -> Dict[str, Any]:
    data = course_in.model_dump()
    data["category"] = course_in.category.value
    data["level"] = course_in.level.value
    if data.get("instructor_id") and ObjectId.is_valid(str(data["instructor_id"])):
        data["instructor_id"] = ObjectId(str(data["instructor_id"]))
    else:
        data["instructor_id"] = None
    result = await db.courses_and_training.insert_one(data)
    data["_id"] = result.inserted_id
    return data

async def update_course(db: AsyncIOMotorDatabase, slug: str, course_in: CourseUpdate) -> Optional[Dict[str, Any]]:
    update_data = course_in.model_dump(exclude_unset=True)
    if "category" in update_data and hasattr(update_data["category"], "value"):
        update_data["category"] = update_data["category"].value
    if "level" in update_data and hasattr(update_data["level"], "value"):
        update_data["level"] = update_data["level"].value
    if "instructor_id" in update_data:
        if update_data["instructor_id"] and ObjectId.is_valid(str(update_data["instructor_id"])): 
            update_data["instructor_id"] = ObjectId(str(update_data["instructor_id"]))
        else:
            update_data["instructor_id"] = None
    
    if update_data:
        await db.courses_and_training.update_one({"slug": slug}, {"$set": update_data})
    return await get_course_by_slug(db, slug)

async def delete_course(db: AsyncIOMotorDatabase, slug: str) -> bool:
    result = await db.courses_and_training.delete_one({"slug": slug})
    return result.deleted_count > 0

async def create_instructor_application(db: AsyncIOMotorDatabase, app_in: InstructorApplicationCreate) -> Dict[str, Any]:
    data = app_in.model_dump()
    data["status"] = ApplicationStatus.SUBMITTED.value
    data["submitted_at"] = datetime.now(timezone.utc)
    result = await db.instructor_applications.insert_one(data)
    data["_id"] = result.inserted_id
    return data

async def get_instructor_applications(
    db: AsyncIOMotorDatabase,
    status: Optional[ApplicationStatus] = None,
    skip: int = 0,
    limit: int = 100
) -> List[Dict[str, Any]]:
    query = {}
    if status:
        query["status"] = status.value
    cursor = db.instructor_applications.find(query).sort("submitted_at", -1).skip(skip).limit(limit)
    return await cursor.to_list(length=limit)

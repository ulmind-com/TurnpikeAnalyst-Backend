from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.mongodb import get_db
from app.schemas.training import CourseResponse, CourseCreate, CourseUpdate, InstructorApplicationCreate, InstructorApplicationResponse
from app.models.enums import CourseCategory, CourseLevel, ApplicationStatus, UserRole
from app.crud.training import get_published_courses, get_course_by_slug, create_instructor_application, get_instructor_applications
from app.api.deps import require_roles

router = APIRouter()

@router.get("/courses", response_model=List[CourseResponse])
async def list_training_courses(
    category: Optional[CourseCategory] = Query(None, description="Filter by training category"),
    level: Optional[CourseLevel] = Query(None, description="Filter by course difficulty level"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=10000),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    courses = await get_published_courses(db, category=category, level=level, skip=skip, limit=limit)
    return courses

@router.get("/courses/{slug}", response_model=CourseResponse)
async def get_course_curriculum_details(slug: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    course = await get_course_by_slug(db, slug)
    if not course:
        raise HTTPException(status_code=404, detail=f"Course with slug '{slug}' not found or not published.")
    return course

@router.post("/courses", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_new_course(course_in: CourseCreate, db: AsyncIOMotorDatabase = Depends(get_db), current_admin: dict = Depends(require_roles([UserRole.ADMIN.value, UserRole.CONSULTANT.value]))):
    from app.crud.training import create_course
    return await create_course(db, course_in)

@router.put("/courses/{slug}", response_model=CourseResponse)
async def update_existing_course(slug: str, course_in: CourseUpdate, db: AsyncIOMotorDatabase = Depends(get_db), current_admin: dict = Depends(require_roles([UserRole.ADMIN.value, UserRole.CONSULTANT.value]))):
    from app.crud.training import update_course
    updated = await update_course(db, slug, course_in)
    if not updated:
        raise HTTPException(status_code=404, detail="Course not found")
    return updated

@router.delete("/courses/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_course(slug: str, db: AsyncIOMotorDatabase = Depends(get_db), current_admin: dict = Depends(require_roles([UserRole.ADMIN.value, UserRole.CONSULTANT.value]))):
    from app.crud.training import delete_course
    deleted = await delete_course(db, slug)
    if not deleted:
        raise HTTPException(status_code=404, detail="Course not found")

@router.post("/become-instructor", response_model=InstructorApplicationResponse, status_code=status.HTTP_201_CREATED)
async def apply_to_become_instructor(app_in: InstructorApplicationCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
    application = await create_instructor_application(db, app_in)
    return application

@router.get("/instructor-applications", response_model=List[InstructorApplicationResponse])
async def review_instructor_applications(
    status_filter: Optional[ApplicationStatus] = Query(None, alias="status", description="Filter by review status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=10000),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(require_roles([UserRole.ADMIN.value, UserRole.CONSULTANT.value, UserRole.INSTRUCTOR.value]))
):
    applications = await get_instructor_applications(db, status=status_filter, skip=skip, limit=limit)
    return applications

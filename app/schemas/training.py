from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from pydantic import Field, EmailStr
from app.schemas.common import BaseSchema, PyObjectId
from app.models.enums import CourseCategory, CourseLevel, ApplicationStatus

class CourseBase(BaseSchema):
    title: str = Field(..., min_length=3, max_length=150)
    slug: str = Field(..., min_length=3, max_length=150)
    category: CourseCategory
    duration_hours: int = Field(..., gt=0)
    level: CourseLevel
    curriculum: List[Dict[str, Any]] = Field(default_factory=list)
    instructor_id: Optional[PyObjectId] = None
    price: float = Field(..., ge=0.0)
    is_published: bool = True

class CourseCreate(CourseBase):
    pass

class CourseUpdate(BaseSchema):
    title: Optional[str] = None
    slug: Optional[str] = None
    category: Optional[CourseCategory] = None
    duration_hours: Optional[int] = Field(None, gt=0)
    level: Optional[CourseLevel] = None
    curriculum: Optional[List[Dict[str, Any]]] = None
    instructor_id: Optional[PyObjectId] = None
    price: Optional[float] = Field(None, ge=0.0)
    is_published: Optional[bool] = None

class CourseResponse(CourseBase):
    id: PyObjectId = Field(default_factory=lambda: "000000000000000000000000", alias="_id")

class InstructorApplicationBase(BaseSchema):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: str
    expertise_areas: List[str] = Field(default_factory=list)
    resume_url: str

class InstructorApplicationCreate(InstructorApplicationBase):
    pass

class InstructorApplicationResponse(InstructorApplicationBase):
    id: PyObjectId = Field(default_factory=lambda: "000000000000000000000000", alias="_id")
    status: ApplicationStatus = ApplicationStatus.SUBMITTED
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

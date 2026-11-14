from datetime import datetime, timezone
from typing import List, Optional
from pydantic import Field
from app.schemas.common import BaseSchema, PyObjectId
from app.schemas.common import BaseSchema, PyObjectId
class ServiceSection(BaseSchema):
    heading: str
    text: str

class ServiceBase(BaseSchema):
    title: str = Field(..., min_length=3, max_length=150)
    slug: str = Field(..., min_length=3, max_length=150)
    parent_category: str
    sub_service_type: str
    short_description: str = Field(..., max_length=500)
    full_description: str
    supported_platforms: List[str] = Field(default_factory=list)
    is_featured: bool = False
    sections: List[ServiceSection] = Field(default_factory=list)

class ServiceCreate(ServiceBase):
    pass

class ServiceUpdate(BaseSchema):
    title: Optional[str] = None
    slug: Optional[str] = None
    parent_category: Optional[str] = None
    sub_service_type: Optional[str] = None
    short_description: Optional[str] = None
    full_description: Optional[str] = None
    supported_platforms: Optional[List[str]] = None
    is_featured: Optional[bool] = None
    sections: Optional[List[ServiceSection]] = None

class ServiceResponse(ServiceBase):
    id: PyObjectId = Field(default_factory=lambda: "000000000000000000000000", alias="_id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

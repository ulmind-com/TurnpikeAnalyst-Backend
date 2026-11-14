from datetime import datetime, timezone
from typing import List, Optional
from pydantic import Field
from app.schemas.common import BaseSchema, PyObjectId

class IndustrySection(BaseSchema):
    heading: str
    text: str

class IndustryBase(BaseSchema):
    title: str = Field(..., min_length=3, max_length=150)
    slug: str = Field(..., min_length=3, max_length=150)
    parent_category: str
    short_description: str = Field(..., max_length=500)
    full_description: str
    supported_platforms: List[str] = Field(default_factory=list)
    is_featured: bool = False
    sections: List[IndustrySection] = Field(default_factory=list)

class IndustryCreate(IndustryBase):
    pass

class IndustryUpdate(BaseSchema):
    title: Optional[str] = None
    slug: Optional[str] = None
    parent_category: Optional[str] = None
    short_description: Optional[str] = None
    full_description: Optional[str] = None
    supported_platforms: Optional[List[str]] = None
    is_featured: Optional[bool] = None
    sections: Optional[List[IndustrySection]] = None

class IndustryResponse(IndustryBase):
    id: str = Field(alias="_id")
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            PyObjectId: str
        }

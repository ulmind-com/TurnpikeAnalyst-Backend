from datetime import datetime, timezone
from typing import List, Optional
from pydantic import Field
from app.schemas.common import BaseSchema, PyObjectId
from app.models.enums import BlogCategory

class BlogBase(BaseSchema):
    title: str = Field(..., min_length=3, max_length=200)
    slug: str = Field(..., min_length=3, max_length=200)
    category: BlogCategory = BlogCategory.UNCATEGORIZED
    author: str = Field(..., min_length=2, max_length=100)
    content_html: str = Field(..., min_length=10)
    summary: str = Field(..., min_length=10, max_length=500)
    tags: List[str] = Field(default_factory=list)
    is_published: bool = True

class BlogCreate(BlogBase):
    pass

class BlogResponse(BlogBase):
    id: PyObjectId = Field(default_factory=lambda: "000000000000000000000000", alias="_id")
    published_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

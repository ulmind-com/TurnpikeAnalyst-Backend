from datetime import datetime, timezone
from typing import Optional
from pydantic import Field
from app.schemas.common import BaseSchema, PyObjectId

class AssetBase(BaseSchema):
    filename: str
    url: str
    content_type: str
    size_bytes: int
    uploaded_by: Optional[str] = None

class AssetCreate(AssetBase):
    pass

class AssetResponse(AssetBase):
    id: PyObjectId = Field(default_factory=lambda: "000000000000000000000000", alias="_id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

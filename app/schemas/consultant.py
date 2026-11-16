from pydantic import Field
from datetime import datetime, timezone
from typing import Optional
from app.schemas.common import BaseSchema, PyObjectId

class ConsultantBase(BaseSchema):
    name: str = Field(..., min_length=2, max_length=100)
    role_description: str = Field(..., min_length=5, max_length=500)
    avatar_url: str = Field(..., min_length=5, max_length=300)
    is_active: bool = Field(default=True)

class ConsultantCreate(ConsultantBase):
    pass

class ConsultantUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    role_description: Optional[str] = Field(None, min_length=5, max_length=500)
    avatar_url: Optional[str] = Field(None, min_length=5, max_length=300)
    is_active: Optional[bool] = None

class ConsultantResponse(ConsultantBase):
    id: PyObjectId = Field(alias="_id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

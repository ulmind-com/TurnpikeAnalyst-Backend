from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import Field
from app.schemas.common import BaseSchema, PyObjectId

class ActivityLogBase(BaseSchema):
    action: str
    resource: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class ActivityLogCreate(ActivityLogBase):
    pass

class ActivityLogResponse(ActivityLogBase):
    id: PyObjectId = Field(default_factory=lambda: "000000000000000000000000", alias="_id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

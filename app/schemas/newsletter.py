from datetime import datetime, timezone
from pydantic import Field, EmailStr
from app.schemas.common import BaseSchema, PyObjectId

class NewsletterSubscribe(BaseSchema):
    email: EmailStr

class NewsletterResponse(BaseSchema):
    id: PyObjectId = Field(default_factory=lambda: "000000000000000000000000", alias="_id")
    email: EmailStr
    subscribed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True

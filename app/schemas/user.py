from datetime import datetime, timezone
from typing import Optional
from pydantic import EmailStr, Field
from app.schemas.common import BaseSchema, PyObjectId
from app.models.enums import UserRole

class UserBase(BaseSchema):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = None
    company: Optional[str] = None
    role: UserRole = UserRole.CLIENT
    avatar_url: Optional[str] = None
    title: Optional[str] = None
    bio: Optional[str] = None
    # Persisted UI preference, so a signed-in user keeps their theme across devices.
    theme: Optional[str] = "light"

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters long")

class UserUpdate(BaseSchema):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    avatar_url: Optional[str] = None
    title: Optional[str] = None
    bio: Optional[str] = None
    is_active: Optional[bool] = None
    theme: Optional[str] = None

class UserResponse(UserBase):
    id: PyObjectId = Field(default_factory=lambda: "000000000000000000000000", alias="_id")
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserInDB(UserResponse):
    hashed_password: str

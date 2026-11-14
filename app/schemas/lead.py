from datetime import datetime, timezone, timedelta
from typing import Optional
from pydantic import Field, EmailStr
from app.schemas.common import BaseSchema, PyObjectId
from app.models.enums import LeadType, Department, LeadStatus

class LeadBase(BaseSchema):
    type: LeadType
    full_name: str = Field(..., min_length=0, max_length=100)
    email: EmailStr
    phone: str = Field(..., min_length=0, max_length=30)
    company: str = Field(..., min_length=0, max_length=150)
    department: Department = Department.HELP_DESK
    subject: str = Field(..., min_length=0, max_length=200)
    message: str = Field(..., min_length=0, max_length=2000)
    service_id: Optional[PyObjectId] = None

class LeadCreate(LeadBase):
    pass

class BookCallCreate(LeadBase):
    type: LeadType = LeadType.BOOK_CALL

class SubmitNeedsCreate(LeadBase):
    type: LeadType = LeadType.REQUIREMENT_FORM

class LeadStatusUpdate(BaseSchema):
    status: LeadStatus

class LeadResponse(LeadBase):
    id: PyObjectId = Field(default_factory=lambda: "000000000000000000000000", alias="_id")
    status: LeadStatus = LeadStatus.PENDING
    sla_reply_deadline: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(hours=8))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

"""Certificate templates and issued certificates.

A template is a background image plus the positions of the few pieces of
text stamped onto it. Keeping positions as data means the design can change
without a code change, and it is what lets the admin panel offer a visual
editor: the editor writes these coordinates.
"""

from datetime import datetime, timezone
from typing import List, Optional

from pydantic import Field

from app.schemas.common import BaseSchema


class TemplateField(BaseSchema):
    """One run of text stamped onto the background.

    Coordinates are in template pixels — the same space as the background
    image — so the admin editor can position by dragging on the image itself
    and store exactly what it sees.
    """

    key: str = Field(
        ...,
        description=(
            "recipient_name | project_title | duration | issued_on | "
            "certificate_number | track_title | custom"
        ),
    )
    # Used only when key == "custom".
    text: Optional[str] = None

    x: int = Field(..., ge=0)
    y: int = Field(..., ge=0)
    font_size: int = Field(default=48, ge=6, le=400)
    font_weight: str = Field(default="bold", description="regular | bold")
    color: str = Field(default="#0B2B33", pattern=r"^#[0-9A-Fa-f]{6}$")
    align: str = Field(default="center", description="left | center | right")
    # Longer names are shrunk to fit rather than overflowing the artwork.
    max_width: Optional[int] = Field(None, ge=10)


class CertificateTemplateBase(BaseSchema):
    name: str = Field(..., min_length=2, max_length=120)
    background_url: str = Field(..., description="Path or URL of the background image.")
    width: int = Field(..., ge=100, le=10000)
    height: int = Field(..., ge=100, le=10000)
    fields: List[TemplateField] = Field(default_factory=list)
    is_active: bool = False


class CertificateTemplateCreate(CertificateTemplateBase):
    pass


class CertificateTemplateUpdate(BaseSchema):
    name: Optional[str] = None
    background_url: Optional[str] = None
    width: Optional[int] = Field(None, ge=100, le=10000)
    height: Optional[int] = Field(None, ge=100, le=10000)
    fields: Optional[List[TemplateField]] = None
    is_active: Optional[bool] = None


class CertificateTemplateResponse(CertificateTemplateBase):
    id: str = Field(alias="_id")
    created_at: datetime
    updated_at: datetime


class CertificateResponse(BaseSchema):
    id: str = Field(alias="_id")
    # Public, human-quotable identifier used by the verification page.
    certificate_number: str
    recipient_name: str
    user_id: str
    enrollment_id: str
    track_title: str
    issued_at: datetime
    pdf_url: str
    revoked: bool = False
    revoked_reason: Optional[str] = None


class CertificateVerification(BaseSchema):
    """Deliberately narrow: enough to confirm a certificate is real, and
    nothing that would expose the holder's account."""

    certificate_number: str
    recipient_name: str
    track_title: str
    issued_at: datetime
    valid: bool
    revoked: bool = False
    issuer: str = "Turnpike Analyst"

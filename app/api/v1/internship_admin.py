"""Admin routes for the internship programme.

Three responsibilities: publish the project briefs, read submissions with
their automated review attached, and decide. Approving a submission is what
issues the certificate — the automated review informs that decision, it does
not make it.
"""

from __future__ import annotations

import io
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from motor.motor_asyncio import AsyncIOMotorDatabase
from PIL import Image

from app.api.deps import get_current_admin
from app.core.config import settings
from app.crud import certificate as certificate_crud
from app.crud import internship as crud
from app.db.mongodb import get_db
from app.models.enums import InternshipStatus
from app.services.email import send_certificate_email
from app.schemas.certificate import (
    CertificateResponse,
    CertificateTemplateCreate,
    CertificateTemplateResponse,
    CertificateTemplateUpdate,
    TemplateField,
)
from app.schemas.internship import (
    AdminDecision,
    EnrollmentResponse,
    InternshipSettings,
    InternshipSettingsUpdate,
    TrackCreate,
    TrackResponse,
    TrackUpdate,
)
from app.services.storage import StorageError, delete_file, fetch, store
from app.services.certificate_render import (
    CertificateRenderError,
    generate_certificate_number,
    render_certificate,
)

logger = logging.getLogger("uvicorn.error")
router = APIRouter()

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def _with_archive_url(enrollment: Dict[str, Any]) -> Dict[str, Any]:
    """Attach the archive download link an admin uses. The archive is served
    by the intern router's ownership-checked route, which also admits admins,
    so there is one download endpoint rather than two."""
    meta = enrollment.get("source_archive")
    if not meta:
        return enrollment
    return {
        **enrollment,
        "source_archive": {
            **meta,
            "download_url": (
                f"/api/v1/internship/me/enrollments/"
                f"{enrollment['_id']}/source-archive"
            ),
        },
    }


async def _attach_user(db: AsyncIOMotorDatabase, enrollment: Dict[str, Any]) -> Dict[str, Any]:
    """Join the intern's name + email onto a single submission for the admin."""
    uid = enrollment.get("user_id")
    user = None
    if uid and ObjectId.is_valid(uid):
        user = await db.users.find_one({"_id": ObjectId(uid)}, {"full_name": 1, "email": 1})
    user = user or {}
    return {**enrollment, "user_name": user.get("full_name"), "user_email": user.get("email")}


async def _attach_users(db: AsyncIOMotorDatabase, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Batch version of :func:`_attach_user` — one query for the whole page."""
    ids = [ObjectId(r["user_id"]) for r in rows if r.get("user_id") and ObjectId.is_valid(r["user_id"])]
    users: Dict[str, Dict[str, Any]] = {}
    if ids:
        async for u in db.users.find({"_id": {"$in": ids}}, {"full_name": 1, "email": 1}):
            users[str(u["_id"])] = u
    out: List[Dict[str, Any]] = []
    for r in rows:
        u = users.get(str(r.get("user_id"))) or {}
        out.append({**r, "user_name": u.get("full_name"), "user_email": u.get("email")})
    return out


# --------------------------------------------------------------------------
# Settings
# --------------------------------------------------------------------------

@router.get("/settings", response_model=InternshipSettings)
async def read_settings(
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: Dict[str, Any] = Depends(get_current_admin),
):
    return await crud.get_settings(db)


@router.patch("/settings", response_model=InternshipSettings)
async def write_settings(
    payload: InternshipSettingsUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: Dict[str, Any] = Depends(get_current_admin),
):
    return await crud.update_settings(db, payload.model_dump(exclude_unset=True))


# --------------------------------------------------------------------------
# Tracks
# --------------------------------------------------------------------------

@router.get("/tracks", response_model=List[TrackResponse])
async def admin_list_tracks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: Dict[str, Any] = Depends(get_current_admin),
):
    return await crud.list_tracks(db, published_only=False, skip=skip, limit=limit)


@router.post("/tracks", response_model=TrackResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_track(
    payload: TrackCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: Dict[str, Any] = Depends(get_current_admin),
):
    if await crud.get_track_by_slug(db, payload.slug, published_only=False):
        raise HTTPException(status_code=409, detail="A track with that slug already exists")
    return await crud.create_track(db, payload)


@router.put("/tracks/{track_id}", response_model=TrackResponse)
async def admin_update_track(
    track_id: str,
    payload: TrackUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: Dict[str, Any] = Depends(get_current_admin),
):
    track = await crud.update_track(db, track_id, payload)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    return track


@router.delete("/tracks/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_track(
    track_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: Dict[str, Any] = Depends(get_current_admin),
):
    if not await crud.delete_track(db, track_id):
        raise HTTPException(status_code=404, detail="Track not found")


# --------------------------------------------------------------------------
# Submissions
# --------------------------------------------------------------------------

@router.get("/submissions", response_model=List[EnrollmentResponse])
async def admin_list_submissions(
    status_filter: Optional[InternshipStatus] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: Dict[str, Any] = Depends(get_current_admin),
):
    rows = await crud.list_enrollments(
        db,
        status=status_filter.value if status_filter else None,
        skip=skip,
        limit=limit,
    )
    return await _attach_users(db, [_with_archive_url(row) for row in rows])


@router.get("/submissions/{enrollment_id}", response_model=EnrollmentResponse)
async def admin_read_submission(
    enrollment_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: Dict[str, Any] = Depends(get_current_admin),
):
    enrollment = await crud.get_enrollment(db, enrollment_id)
    if not enrollment:
        raise HTTPException(status_code=404, detail="Submission not found")
    return await _attach_user(db, _with_archive_url(enrollment))


@router.delete("/submissions/{enrollment_id}/source-archive", response_model=EnrollmentResponse)
async def admin_delete_source_archive(
    enrollment_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_admin: Dict[str, Any] = Depends(get_current_admin),
):
    """Permanently delete an intern's uploaded source archive (.zip) from
    Cloudinary/local storage and MongoDB to prevent storage bloat."""
    enrollment = await crud.get_enrollment(db, enrollment_id)
    if not enrollment:
        raise HTTPException(status_code=404, detail="Submission not found")

    meta = enrollment.get("source_archive")
    if meta and meta.get("storage_key"):
        try:
            await delete_file(
                meta["storage_key"],
                private=True,
                resource_type="raw",
                backend=meta.get("storage_backend"),
            )
        except StorageError as exc:
            logger.warning("Admin delete source archive storage warning: %s", exc)

    updated = await crud.set_enrollment_fields(
        db,
        enrollment_id,
        {"source_archive": None},
    )
    logger.info(
        "Admin %s deleted source archive for enrollment %s",
        current_admin.get("_id"),
        enrollment_id,
    )
    return await _attach_user(db, _with_archive_url(updated))


@router.post("/submissions/{enrollment_id}/decision", response_model=EnrollmentResponse)
async def admin_decide(
    enrollment_id: str,
    payload: AdminDecision,
    background: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_admin: Dict[str, Any] = Depends(get_current_admin),
):
    """Approve or reject. Approval issues the certificate in the same call,
    so there is no window in which a submission is approved but the intern
    has nothing to show for it."""
    enrollment = await crud.get_enrollment(db, enrollment_id)
    if not enrollment:
        raise HTTPException(status_code=404, detail="Submission not found")

    decidable = {
        InternshipStatus.UNDER_REVIEW.value,
        InternshipStatus.QUESTIONS_PENDING.value,
        InternshipStatus.REVIEW_FAILED.value,
    }
    if enrollment["status"] not in decidable:
        raise HTTPException(
            status_code=409,
            detail=f"A submission in state {enrollment['status']} cannot be decided.",
        )

    # The reviewer model cannot watch the recording, so an approval has to
    # carry a person's word that someone did. Without this the certificate
    # would be attesting to something nobody checked.
    if payload.approved and not payload.demo_verified:
        raise HTTPException(
            status_code=422,
            detail="Confirm you watched the demo recording before approving.",
        )

    now = datetime.now(timezone.utc)
    changes: Dict[str, Any] = {
        "decision": {
            "approved": payload.approved,
            "notes": payload.notes,
            "demo_verified": payload.demo_verified,
            "decided_by": str(current_admin["_id"]),
            "decided_at": now,
        },
        "status": (
            InternshipStatus.APPROVED.value
            if payload.approved
            else InternshipStatus.REJECTED.value
        ),
    }

    if payload.approved:
        certificate = await _issue_certificate(db, enrollment)
        changes["certificate_id"] = certificate["_id"]

        try:
            user_doc = (
                await db.users.find_one({"_id": ObjectId(enrollment["user_id"])})
                if ObjectId.is_valid(enrollment.get("user_id", ""))
                else None
            )
            if user_doc and user_doc.get("email"):
                background.add_task(
                    send_certificate_email,
                    user_email=user_doc["email"],
                    user_name=user_doc.get("full_name") or "",
                    project_title=enrollment.get("project_title") or "Internship Project",
                    certificate_number=certificate.get("certificate_number") or "",
                    pdf_url=certificate.get("pdf_url") or "",
                )
        except Exception as mail_exc:
            logger.warning("Could not queue certificate email for %s: %s", enrollment_id, mail_exc)

    # Once a submission is decided (approved or rejected) the source archive has
    # served its purpose — the automated review already read it, and a decision
    # is terminal. Deleting it here keeps storage from accumulating a zip per
    # intern forever; the full source stays available on the intern's GitHub
    # repositories. Best-effort: a storage hiccup must not fail the decision.
    meta = enrollment.get("source_archive")
    if meta and meta.get("storage_key"):
        try:
            await delete_file(
                meta["storage_key"],
                private=True,
                resource_type="raw",
                backend=meta.get("storage_backend"),
            )
        except StorageError as exc:
            logger.warning("Could not delete source archive on decision for %s: %s", enrollment_id, exc)
    changes["source_archive"] = None

    updated = await crud.set_enrollment_fields(db, enrollment_id, changes)
    return await _attach_user(db, _with_archive_url(updated))


async def _issue_certificate(
    db: AsyncIOMotorDatabase, enrollment: Dict[str, Any]
) -> Dict[str, Any]:
    """Render and record the certificate for an approved submission."""
    existing = await db.certificates.find_one({"enrollment_id": enrollment["_id"]})
    if existing:
        # Re-approving must not mint a second certificate for the same work.
        return {**existing, "_id": str(existing["_id"])}

    template = await certificate_crud.get_active_template(db)
    if not template:
        raise HTTPException(
            status_code=409,
            detail="No active certificate template. Upload and activate one before approving.",
        )

    user = (
        await db.users.find_one({"_id": ObjectId(enrollment["user_id"])})
        if ObjectId.is_valid(enrollment["user_id"])
        else None
    )
    recipient_name = (user or {}).get("full_name") or "Turnpike Intern"

    number = generate_certificate_number()

    # Older enrollments predate project_title; fall back to the track name.
    project_title = enrollment.get("project_title") or enrollment.get("track_title") or "Project"
    months = enrollment.get("duration_months") or 1
    duration = f"{months} month" if months == 1 else f"{months} months"

    try:
        background = await fetch(
            template.get("storage_key") or template["background_url"], private=False
        )
        pdf = render_certificate(
            background=background,
            width=template["width"],
            height=template["height"],
            fields=[TemplateField(**field) for field in template.get("fields", [])],
            values={
                "recipient_name": recipient_name,
                "project_title": project_title,
                "duration": duration,
                # Kept so templates built before projects had their own title
                # keep rendering.
                "track_title": enrollment.get("track_title") or project_title,
                "issued_on": datetime.now(timezone.utc).strftime("%d %B %Y"),
                "certificate_number": number,
            },
        )
        stored_pdf = await store(
            pdf,
            folder="certificates",
            filename=f"{number}.pdf",
            private=False,
            # Cloudinary classes a PDF as "raw", not an image.
            resource_type="raw",
        )
    except (CertificateRenderError, StorageError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return await certificate_crud.create_certificate(
        db,
        {
            "certificate_number": number,
            "recipient_name": recipient_name,
            "user_id": enrollment["user_id"],
            "enrollment_id": enrollment["_id"],
            "track_title": project_title,
            "template_id": template["_id"],
            "issued_at": datetime.now(timezone.utc),
            "pdf_url": stored_pdf.url or f"/uploads/certificates/{number}.pdf",
            "revoked": False,
            "revoked_reason": None,
        },
    )


# --------------------------------------------------------------------------
# Certificate templates
# --------------------------------------------------------------------------

@router.get("/certificate-templates", response_model=List[CertificateTemplateResponse])
async def admin_list_templates(
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: Dict[str, Any] = Depends(get_current_admin),
):
    return await certificate_crud.list_templates(db)


@router.post("/certificate-templates/background")
async def admin_upload_background(
    file: UploadFile = File(...),
    _: Dict[str, Any] = Depends(get_current_admin),
):
    """Store a certificate background and report its pixel size.

    The editor needs the real dimensions to place fields against, so they are
    measured here rather than trusted from the client.
    """
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Background must be a PNG, JPEG or WebP image.",
        )

    payload = await file.read()
    if len(payload) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Background must be 10 MB or smaller.")

    # The client-supplied filename never reaches the filesystem; only its
    # extension is kept, and the stored name is generated.
    suffix = Path(file.filename or "").suffix.lower()
    if not re.fullmatch(r"\.(png|jpe?g|webp)", suffix):
        suffix = ".png"
    stored_name = f"{uuid.uuid4().hex}{suffix}"

    # Measured before storing, so a file that is not really an image never
    # reaches the bucket.
    try:
        with Image.open(io.BytesIO(payload)) as image:
            width, height = image.size
    except OSError as exc:
        raise HTTPException(status_code=422, detail=f"Unreadable image: {exc}") from exc

    try:
        stored = await store(
            payload,
            folder="certificate-templates",
            filename=stored_name,
            private=False,
        )
    except StorageError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "background_url": stored.url or f"/uploads/certificate-templates/{stored_name}",
        "storage_key": stored.key,
        "width": width,
        "height": height,
    }


@router.post(
    "/certificate-templates",
    response_model=CertificateTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def admin_create_template(
    payload: CertificateTemplateCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: Dict[str, Any] = Depends(get_current_admin),
):
    return await certificate_crud.create_template(db, payload)


@router.put("/certificate-templates/{template_id}", response_model=CertificateTemplateResponse)
async def admin_update_template(
    template_id: str,
    payload: CertificateTemplateUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: Dict[str, Any] = Depends(get_current_admin),
):
    template = await certificate_crud.update_template(db, template_id, payload)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.delete("/certificate-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_template(
    template_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: Dict[str, Any] = Depends(get_current_admin),
):
    if not await certificate_crud.delete_template(db, template_id):
        raise HTTPException(status_code=404, detail="Template not found")


@router.post("/certificate-templates/{template_id}/preview")
async def admin_preview_template(
    template_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: Dict[str, Any] = Depends(get_current_admin),
):
    """Render the template with sample values so the admin can check
    placement before any real certificate is issued."""
    template = await certificate_crud.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    preview_name = f"preview-{template_id}.pdf"
    try:
        background = await fetch(
            template.get("storage_key") or template["background_url"], private=False
        )
        pdf = render_certificate(
            background=background,
            width=template["width"],
            height=template["height"],
            fields=[TemplateField(**field) for field in template.get("fields", [])],
            values={
                "recipient_name": "Ananya Chatterjee",
                "project_title": "Shipment Trace API",
                "duration": "2 months",
                "track_title": "Shipment Trace API",
                "issued_on": datetime.now(timezone.utc).strftime("%d %B %Y"),
                "certificate_number": "TA-2026-PREVIEW01",
            },
        )
        stored_preview = await store(
            pdf, folder="certificates", filename=preview_name, private=False, resource_type="raw"
        )
    except (CertificateRenderError, StorageError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {"preview_url": stored_preview.url or f"/uploads/certificates/{preview_name}"}


# --------------------------------------------------------------------------
# Issued certificates
# --------------------------------------------------------------------------

@router.get("/certificates", response_model=List[CertificateResponse])
async def admin_list_certificates(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: Dict[str, Any] = Depends(get_current_admin),
):
    cursor = db.certificates.find().sort("issued_at", -1).skip(skip).limit(limit)
    return [{**doc, "_id": str(doc["_id"])} async for doc in cursor]


@router.post("/certificates/{certificate_id}/revoke", response_model=CertificateResponse)
async def admin_revoke_certificate(
    certificate_id: str,
    reason: str = Query(..., min_length=3, max_length=500),
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: Dict[str, Any] = Depends(get_current_admin),
):
    certificate = await certificate_crud.revoke_certificate(db, certificate_id, reason)
    if not certificate:
        raise HTTPException(status_code=404, detail="Certificate not found")
    return certificate

"""Intern-facing internship routes.

The flow these endpoints implement:

    browse tracks → enrol (starts the build clock)
    → inspect GitHub repo(s) + live URL + upload .zip source archive
    → submit dossier → automated review reads repo(s), .zip and live site,
      and writes 5–7 project-specific follow-up questions
    → intern answers (anti-paste + telemetry) → authenticity check runs
    → human reviewer decides → certificate
"""

from __future__ import annotations

import asyncio
import io
import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple

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
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from PIL import Image

from app.api.deps import get_current_active_user
from app.crud import certificate as certificate_crud
from app.crud import internship as crud
from app.db.mongodb import get_db
from app.models.enums import EnrollmentMode, InternshipStatus, UserRole
from app.schemas.certificate import CertificateResponse, CertificateVerification
from app.schemas.internship import (
    AnswerSubmission,
    AttachmentResponse,
    EnrollmentCreate,
    EnrollmentPublic,
    LiveSitePrecheckResult,
    RepoPrecheckResult,
    SourceAnalysisRequest,
    SourceAnalysisResponse,
    SourceArchiveMeta,
    SubmissionCreate,
    TrackResponse,
)
from app.services.ai_review import ReviewUnavailable, get_review_provider
from app.services.github_repo import RepoAccessError, RepoSnapshot, fetch_repo_snapshot
from app.services.live_site import LiveSiteSnapshot, fetch_live_site_snapshot
from app.services.source_archive import ArchiveError, ArchiveSnapshot, digest_archive
from app.services.storage import StorageError, delete_file, fetch, store
from app.services.email import send_enrollment_email, send_questions_ready_email
from bson import ObjectId

logger = logging.getLogger("uvicorn.error")
router = APIRouter()


# --------------------------------------------------------------------------
# Tracks
# --------------------------------------------------------------------------

@router.get("/tracks", response_model=List[TrackResponse])
async def list_tracks(
    category: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    return await crud.list_tracks(db, category=category, skip=skip, limit=limit)


@router.get("/tracks/{slug}", response_model=TrackResponse)
async def get_track(slug: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    track = await crud.get_track_by_slug(db, slug)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    return track


# --------------------------------------------------------------------------
# Enrollment
# --------------------------------------------------------------------------

@router.post("/enroll", response_model=EnrollmentPublic, status_code=status.HTTP_201_CREATED)
async def enroll(
    payload: EnrollmentCreate,
    background: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    user_id = str(current_user["_id"])
    settings_doc = await crud.get_settings(db)

    if payload.duration_months not in settings_doc.allowed_durations:
        allowed = ", ".join(f"{month} month" for month in settings_doc.allowed_durations)
        raise HTTPException(
            status_code=422, detail=f"Choose one of the available durations: {allowed}."
        )

    track: Dict[str, Any] | None = None
    if payload.mode == EnrollmentMode.TRACK:
        track = await crud.get_track(db, payload.track_id or "")
        if not track or not track.get("is_published"):
            raise HTTPException(status_code=404, detail="Track not found")

        existing = await crud.get_enrollment_for_user_and_track(db, user_id, payload.track_id)
        if existing:
            raise HTTPException(
                status_code=409, detail="You are already enrolled on this project."
            )
        project_title = track["title"]
        project_summary = track.get("summary")
    else:
        project_title = payload.own_project.title
        project_summary = payload.own_project.summary

    if not settings_doc.allow_parallel_enrollments:
        active = await crud.count_active_enrollments(db, user_id)
        if active:
            raise HTTPException(
                status_code=409,
                detail="Finish your current project before starting another one.",
            )

    created = await crud.create_enrollment(
        db,
        user_id=user_id,
        mode=payload.mode.value,
        duration_months=payload.duration_months,
        project_title=project_title,
        project_summary=project_summary,
        track=track,
    )
    if current_user.get("email"):
        background.add_task(
            send_enrollment_email,
            user_email=current_user["email"],
            user_name=current_user.get("full_name") or "",
            project_title=project_title,
            duration_months=payload.duration_months,
            deadline_at=created["deadline_at"],
        )
    return _public_view(created)


@router.get("/me/enrollments", response_model=List[EnrollmentPublic])
async def my_enrollments(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    rows = await crud.list_enrollments_for_user(db, str(current_user["_id"]))
    return [_public_view(row) for row in rows]


def _public_view(enrollment: Dict[str, Any]) -> Dict[str, Any]:
    """Shape a stored enrollment for the intern.

    Reviewer-only fields (ai_review, review_error, answer_analysis, question
    expects, and typing telemetry) are stripped so the intern never sees scores
    or rubric hints.
    """
    decision = enrollment.get("decision") or {}
    archive = enrollment.get("source_archive")
    if archive:
        archive = {
            **archive,
            "download_url": (
                f"/api/v1/internship/me/enrollments/"
                f"{enrollment['_id']}/source-archive"
            ),
        }

    sanitized_questions = [
        {
            "id": q["id"],
            "question": q["question"],
            "answer": q.get("answer"),
            "answered_at": q.get("answered_at"),
        }
        for q in (enrollment.get("questions") or [])
    ]

    return {
        **enrollment,
        "source_archive": archive,
        "questions": sanitized_questions,
        "decision_notes": decision.get("notes"),
        "review_failed": bool(enrollment.get("review_error")),
    }


async def _owned_enrollment(
    db: AsyncIOMotorDatabase, enrollment_id: str, user_id: str
) -> Dict[str, Any]:
    enrollment = await crud.get_enrollment(db, enrollment_id)
    if not enrollment or enrollment["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    return enrollment


@router.get("/me/enrollments/{enrollment_id}", response_model=EnrollmentPublic)
async def my_enrollment(
    enrollment_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    return _public_view(await _owned_enrollment(db, enrollment_id, str(current_user["_id"])))


# --------------------------------------------------------------------------
# Pre-submission live source analysis (GitHub repos + live URL)
# --------------------------------------------------------------------------

@router.post(
    "/me/enrollments/{enrollment_id}/analyze-sources",
    response_model=SourceAnalysisResponse,
)
async def analyze_sources(
    enrollment_id: str,
    payload: SourceAnalysisRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Inspect submitted GitHub repositories and deployed URL immediately.

    Gives the intern real-time diagnostics (accessibility, detected stack,
    commits, live HTTP check) before they proceed through the submission wizard.
    """
    user_id = str(current_user["_id"])
    await _owned_enrollment(db, enrollment_id, user_id)

    async def inspect_repo(entry: Any) -> Tuple[RepoPrecheckResult, RepoSnapshot | None]:
        url_str = str(entry.url)
        try:
            snap = await fetch_repo_snapshot(url_str)
            return (
                RepoPrecheckResult(
                    url=url_str,
                    role=entry.role,
                    label=entry.label,
                    accessible=True,
                    owner=snap.owner,
                    name=snap.name,
                    default_branch=snap.default_branch,
                    languages=snap.languages,
                    commit_count=snap.commit_count,
                    distinct_commit_days=snap.distinct_commit_days,
                    file_count=len(snap.tree),
                    has_tests=snap.has_tests,
                    has_readme=snap.has_readme,
                    is_fork=snap.is_fork,
                ),
                snap,
            )
        except RepoAccessError as exc:
            return (
                RepoPrecheckResult(
                    url=url_str,
                    role=entry.role,
                    label=entry.label,
                    accessible=False,
                    error=str(exc),
                ),
                None,
            )
        except Exception as exc:
            return (
                RepoPrecheckResult(
                    url=url_str,
                    role=entry.role,
                    label=entry.label,
                    accessible=False,
                    error=f"Could not inspect repository: {exc}",
                ),
                None,
            )

    repo_tasks = [inspect_repo(entry) for entry in payload.repositories]
    live_task = (
        fetch_live_site_snapshot(str(payload.live_url)) if payload.live_url else None
    )

    if live_task is not None:
        *repo_pairs, live_snap = await asyncio.gather(*repo_tasks, live_task)
    else:
        repo_pairs = await asyncio.gather(*repo_tasks)
        live_snap = None

    repo_results: List[RepoPrecheckResult] = [pair[0] for pair in repo_pairs]
    warnings: List[str] = []
    detected_set: set[str] = set()

    for res in repo_results:
        if not res.accessible:
            warnings.append(f"{res.url}: {res.error or 'Repository is unreachable or private.'}")
            continue
        if res.file_count == 0:
            warnings.append(f"{res.owner}/{res.name} appears empty (0 source files).")
        if res.is_fork:
            warnings.append(
                f"{res.owner}/{res.name} is a fork — ensure your original contributions are clear."
            )
        if not res.has_readme:
            warnings.append(f"{res.owner}/{res.name} has no README.")
        for lang in res.languages.keys():
            detected_set.add(lang)

    live_result: LiveSitePrecheckResult | None = None
    if live_snap is not None:
        live_result = LiveSitePrecheckResult(
            url=live_snap.url,
            final_url=live_snap.final_url,
            reachable=live_snap.reachable,
            status_code=live_snap.status_code,
            title=live_snap.title,
            detected_tech=live_snap.detected_tech,
            is_placeholder_or_parked=live_snap.is_placeholder_or_parked,
            error=live_snap.error,
        )
        for t in live_snap.detected_tech:
            detected_set.add(t)
        if not live_snap.reachable:
            warnings.append(f"Live URL check failed: {live_snap.error or 'Unreachable'}")
        elif live_snap.is_placeholder_or_parked:
            warnings.append(
                "Live URL looks like a placeholder or error page — verify your deployment."
            )

    all_accessible = all(r.accessible for r in repo_results)
    return SourceAnalysisResponse(
        repos=repo_results,
        live_site=live_result,
        detected_technologies=sorted(detected_set),
        warnings=warnings,
        all_accessible=all_accessible,
    )


# --------------------------------------------------------------------------
# Submission and automated review
# --------------------------------------------------------------------------

async def _load_archive_snapshot(
    enrollment: Dict[str, Any],
) -> ArchiveSnapshot | None:
    meta = enrollment.get("source_archive")
    if not meta:
        return None
    key = meta.get("storage_key") or f"internship-archives/{meta.get('stored_name')}"
    backend = meta.get("storage_backend")
    try:
        data = await fetch(key, private=True, resource_type="raw", backend=backend)
        return digest_archive(data, meta.get("filename", "archive.zip"))
    except (StorageError, ArchiveError) as exc:
        logger.warning(
            "Archive digest skipped for enrollment %s: %s", enrollment.get("_id"), exc
        )
        return None


async def run_automated_review(
    enrollment_id: str, track: Dict[str, Any] | None
) -> None:
    """Read all repositories, live URL, and zip archive, and write 5–7 questions."""
    db = get_db()
    try:
        enrollment = await crud.get_enrollment(db, enrollment_id)
        if not enrollment or not enrollment.get("submission"):
            logger.warning("Review skipped: enrollment %s has no submission", enrollment_id)
            return

        settings_doc = await crud.get_settings(db)
        submission = enrollment["submission"]

        repo_entries = submission.get("repositories") or [
            {"url": submission["repo_url"], "role": "monorepo"}
        ]

        repo_tasks = [fetch_repo_snapshot(entry["url"]) for entry in repo_entries]
        live_url = submission.get("live_url")
        live_task = fetch_live_site_snapshot(live_url) if live_url else None

        if live_task is not None:
            *repo_snaps, live_snap = await asyncio.gather(*repo_tasks, live_task)
        else:
            repo_snaps = await asyncio.gather(*repo_tasks)
            live_snap = None

        snapshots_with_roles: List[Tuple[RepoSnapshot, str]] = [
            (snap, entry.get("role", "monorepo"))
            for snap, entry in zip(repo_snaps, repo_entries)
        ]

        archive = await _load_archive_snapshot(enrollment)
        provider = get_review_provider()

        if track:
            brief = track.get("brief", "")
            requirements = track.get("requirements", []) or []
        else:
            brief = (
                f"Intern-proposed project: {enrollment['project_title']}\n\n"
                f"{enrollment.get('project_summary') or ''}"
            )
            requirements = []

        review = await provider.review(
            snapshots_with_roles, brief, requirements, submission, archive, live_snap
        )
        question_count = max(5, min(7, settings_doc.questions_per_submission or 6))
        questions = await provider.follow_up_questions(
            snapshots_with_roles, brief, question_count, submission, archive, live_snap
        )

        await crud.set_enrollment_fields(
            db,
            enrollment_id,
            {
                "ai_review": review.model_dump(),
                "questions": [question.model_dump() for question in questions],
                "status": InternshipStatus.QUESTIONS_PENDING.value,
                "review_error": None,
            },
        )
        logger.info("Review complete for enrollment %s (score %d)", enrollment_id, review.score)

        # Notify intern via email that review is done and questions are waiting
        try:
            user_doc = (
                await db.users.find_one({"_id": ObjectId(enrollment["user_id"])})
                if ObjectId.is_valid(enrollment.get("user_id", ""))
                else None
            )
            if user_doc and user_doc.get("email"):
                await send_questions_ready_email(
                    user_email=user_doc["email"],
                    user_name=user_doc.get("full_name") or "",
                    project_title=enrollment.get("project_title") or "Internship Project",
                    enrollment_id=enrollment_id,
                    question_count=len(questions),
                )
        except Exception as mail_exc:
            logger.warning("Could not send questions ready email for %s: %s", enrollment_id, mail_exc)

    except (RepoAccessError, ReviewUnavailable) as exc:
        logger.warning("Review failed for enrollment %s: %s", enrollment_id, exc)
        await crud.set_enrollment_fields(
            db,
            enrollment_id,
            {"status": InternshipStatus.REVIEW_FAILED.value, "review_error": str(exc)},
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected review failure for enrollment %s", enrollment_id)
        await crud.set_enrollment_fields(
            db,
            enrollment_id,
            {
                "status": InternshipStatus.REVIEW_FAILED.value,
                "review_error": f"Unexpected error: {exc}",
            },
        )


async def run_answer_authenticity_check(enrollment_id: str) -> None:
    """Assess whether submitted answers show signs of AI generation or pasting."""
    db = get_db()
    try:
        enrollment = await crud.get_enrollment(db, enrollment_id)
        if not enrollment:
            return
        questions = enrollment.get("questions") or []
        if not questions:
            return
        submission = enrollment.get("submission") or {}
        summary = (
            f"Project: {enrollment.get('project_title')}\n"
            f"Technologies: {', '.join(submission.get('technologies', []))}\n"
            f"Purpose: {submission.get('purpose', '')[:400]}"
        )
        answers_with_telemetry = [
            {
                "id": q["id"],
                "answer": q.get("answer", ""),
                "telemetry": q.get("telemetry"),
            }
            for q in questions
        ]
        provider = get_review_provider()
        report = await provider.assess_authenticity(
            questions, answers_with_telemetry, summary
        )
        await crud.set_enrollment_fields(
            db, enrollment_id, {"answer_analysis": report.model_dump()}
        )
        logger.info(
            "Authenticity check complete for enrollment %s (score %d, likelihood %s)",
            enrollment_id,
            report.overall_authenticity_score,
            report.ai_generated_likelihood,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Authenticity check failed for enrollment %s", enrollment_id)


@router.post("/me/enrollments/{enrollment_id}/submit", response_model=EnrollmentPublic)
async def submit_project(
    enrollment_id: str,
    payload: SubmissionCreate,
    background: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    user_id = str(current_user["_id"])
    enrollment = await _owned_enrollment(db, enrollment_id, user_id)

    allowed = {InternshipStatus.ENROLLED.value, InternshipStatus.REVIEW_FAILED.value}
    if enrollment["status"] not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"This project cannot be submitted while it is {enrollment['status']}.",
        )

    if not enrollment.get("source_archive"):
        raise HTTPException(
            status_code=422,
            detail="Upload your project source archive (.zip) before submitting.",
        )

    now = datetime.now(timezone.utc)
    deadline = enrollment["deadline_at"]
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    if now > deadline:
        await crud.set_enrollment_fields(
            db, enrollment_id, {"status": InternshipStatus.EXPIRED.value}
        )
        raise HTTPException(
            status_code=409, detail="The build window for this project has closed."
        )

    track = (
        await crud.get_track(db, enrollment["track_id"])
        if enrollment.get("track_id")
        else None
    )

    for diagram in (payload.architecture_diagram, payload.data_flow_diagram):
        if diagram.kind != "image":
            continue
        attachment = await crud.get_attachment(db, diagram.asset_id or "")
        if not attachment or attachment["enrollment_id"] != enrollment_id:
            raise HTTPException(
                status_code=422, detail="A referenced diagram image was not found."
            )

    submission = {
        "repo_url": str(payload.repo_url),
        "repositories": [
            {"url": str(r.url), "role": r.role, "label": r.label}
            for r in payload.repositories
        ],
        "project_architecture_type": payload.project_architecture_type,
        "live_url": str(payload.live_url) if payload.live_url else None,
        "demo_video_url": str(payload.demo_video_url),
        "purpose": payload.purpose.strip(),
        "technologies": payload.technologies,
        "architecture_text": payload.architecture_text.strip(),
        "architecture_diagram": payload.architecture_diagram.model_dump(),
        "data_flow_text": payload.data_flow_text.strip(),
        "data_flow_diagram": payload.data_flow_diagram.model_dump(),
        "use_cases": payload.use_cases,
        "benefits": payload.benefits.strip(),
        "notes": payload.notes,
        "submitted_at": now,
    }

    updated = await crud.set_enrollment_fields(
        db,
        enrollment_id,
        {
            "submission": submission,
            "status": InternshipStatus.AI_REVIEWING.value,
            "questions": [],
            "ai_review": None,
            "answer_analysis": None,
            "review_error": None,
        },
    )

    background.add_task(run_automated_review, enrollment_id, track)
    return _public_view(updated)


@router.post("/me/enrollments/{enrollment_id}/answers", response_model=EnrollmentPublic)
async def submit_answers(
    enrollment_id: str,
    payload: AnswerSubmission,
    background: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    user_id = str(current_user["_id"])
    enrollment = await _owned_enrollment(db, enrollment_id, user_id)

    if enrollment["status"] != InternshipStatus.QUESTIONS_PENDING.value:
        raise HTTPException(
            status_code=409, detail="There are no questions awaiting an answer."
        )

    questions = enrollment.get("questions") or []
    answers = {
        item.id: {
            "answer": item.answer.strip(),
            "telemetry": item.telemetry.model_dump() if item.telemetry else None,
        }
        for item in payload.answers
    }

    missing = [
        question["id"]
        for question in questions
        if not (answers.get(question["id"]) or {}).get("answer")
    ]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"{len(missing)} question(s) still need an answer.",
        )

    now = datetime.now(timezone.utc)
    for question in questions:
        entry = answers[question["id"]]
        question["answer"] = entry["answer"]
        question["answered_at"] = now
        if entry["telemetry"] is not None:
            question["telemetry"] = entry["telemetry"]

    settings_doc = await crud.get_settings(db)
    saved = await crud.set_enrollment_fields(
        db,
        enrollment_id,
        {
            "questions": questions,
            "status": InternshipStatus.UNDER_REVIEW.value,
            "review_due_at": now + timedelta(days=settings_doc.review_sla_days),
        },
    )
    background.add_task(run_answer_authenticity_check, enrollment_id)
    return _public_view(saved)


# --------------------------------------------------------------------------
# Diagram attachments
# --------------------------------------------------------------------------

RASTER_TYPES = {"image/png": "PNG", "image/jpeg": "JPEG", "image/webp": "WEBP"}
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
MAX_ATTACHMENTS_PER_ENROLLMENT = 5


@router.post(
    "/me/enrollments/{enrollment_id}/attachments",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    enrollment_id: str,
    file: UploadFile = File(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    user_id = str(current_user["_id"])
    await _owned_enrollment(db, enrollment_id, user_id)

    if await crud.count_attachments(db, enrollment_id) >= MAX_ATTACHMENTS_PER_ENROLLMENT:
        raise HTTPException(
            status_code=409,
            detail=f"A project may have at most {MAX_ATTACHMENTS_PER_ENROLLMENT} attachments.",
        )

    if file.content_type not in RASTER_TYPES:
        raise HTTPException(
            status_code=415, detail="Diagrams must be a PNG, JPEG or WebP image."
        )

    payload = await file.read()
    if len(payload) > MAX_ATTACHMENT_BYTES:
        raise HTTPException(status_code=413, detail="Each image must be 10 MB or smaller.")

    target_format = RASTER_TYPES[file.content_type]
    try:
        with Image.open(io.BytesIO(payload)) as image:
            image.load()
            cleaned = image.convert("RGB" if target_format == "JPEG" else "RGBA")
            buffer = io.BytesIO()
            cleaned.save(buffer, format=target_format)
    except Exception as exc:
        raise HTTPException(
            status_code=422, detail="That file could not be read as an image."
        ) from exc

    asset_id = uuid.uuid4().hex
    extension = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp"}[target_format]

    try:
        stored_file = await store(
            buffer.getvalue(),
            folder="internship-attachments",
            filename=f"{asset_id}{extension}",
            private=True,
        )
    except StorageError as exc:
        raise HTTPException(status_code=502, detail=f"Could not store the image: {exc}") from exc

    stored = buffer.getbuffer().nbytes
    await crud.create_attachment(
        db,
        {
            "asset_id": asset_id,
            "enrollment_id": enrollment_id,
            "user_id": user_id,
            "filename": (file.filename or "diagram")[:120],
            "content_type": file.content_type,
            "stored_name": f"{asset_id}{extension}",
            "storage_key": stored_file.key,
            "storage_backend": stored_file.backend,
            "size_bytes": stored,
            "uploaded_at": datetime.now(timezone.utc),
        },
    )

    return AttachmentResponse(
        asset_id=asset_id,
        filename=(file.filename or "diagram")[:120],
        content_type=file.content_type,
        size_bytes=stored,
        url=f"/api/v1/internship/attachments/{asset_id}",
    )


@router.get("/attachments/{asset_id}")
async def read_attachment(
    asset_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    attachment = await crud.get_attachment(db, asset_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    is_owner = attachment["user_id"] == str(current_user["_id"])
    is_admin = current_user.get("role") == UserRole.ADMIN.value
    if not (is_owner or is_admin):
        raise HTTPException(status_code=404, detail="Attachment not found")

    key = attachment.get("storage_key") or f"internship-attachments/{attachment['stored_name']}"
    backend = attachment.get("storage_backend")
    try:
        data = await fetch(key, private=True, backend=backend)
    except StorageError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return Response(
        content=data,
        media_type=attachment["content_type"],
        headers={
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; img-src 'self'",
            "Cache-Control": "private, max-age=300",
        },
    )


# --------------------------------------------------------------------------
# Source archive (the project zip)
# --------------------------------------------------------------------------

# Source archives go to S3-compatible storage (Supabase Storage), whose free
# tier caps a single upload at 50 MB — and the archive is deleted on the
# admin's decision, so storage never accumulates. The full source is read
# from the GitHub repo regardless, so the zip is a supporting artefact.
MAX_ARCHIVE_UPLOAD_BYTES = 50 * 1024 * 1024


def _safe_archive_name(raw: str) -> str:
    cleaned = re.sub(r"[^\w.\- ]", "_", (raw or "archive.zip")).strip()
    cleaned = cleaned[:120] or "archive.zip"
    if not cleaned.lower().endswith(".zip"):
        cleaned += ".zip"
    return cleaned


@router.post(
    "/me/enrollments/{enrollment_id}/source-archive",
    response_model=SourceArchiveMeta,
    status_code=status.HTTP_201_CREATED,
)
async def upload_source_archive(
    enrollment_id: str,
    file: UploadFile = File(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    user_id = str(current_user["_id"])
    enrollment = await _owned_enrollment(db, enrollment_id, user_id)

    locked = {
        InternshipStatus.AI_REVIEWING.value,
        InternshipStatus.QUESTIONS_PENDING.value,
        InternshipStatus.UNDER_REVIEW.value,
        InternshipStatus.APPROVED.value,
        InternshipStatus.REJECTED.value,
    }
    if enrollment["status"] in locked:
        raise HTTPException(
            status_code=409,
            detail="The source archive cannot be changed once the project is under review.",
        )

    filename = _safe_archive_name(file.filename or "archive.zip")

    payload = await file.read()
    if len(payload) > MAX_ARCHIVE_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                "The source archive must be 50 MB or smaller. Your full code is still "
                "read from your GitHub repository — the zip is a supporting copy."
            ),
        )

    try:
        digest_archive(payload, filename)
    except ArchiveError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Clean up the previous archive if the intern is replacing it.
    prev_meta = enrollment.get("source_archive")
    if prev_meta and prev_meta.get("storage_key"):
        try:
            await delete_file(
                prev_meta["storage_key"],
                private=True,
                resource_type="raw",
                backend=prev_meta.get("storage_backend"),
            )
        except StorageError as exc:
            logger.warning("Could not remove old archive before replace: %s", exc)

    asset_id = uuid.uuid4().hex
    stored_name = f"{asset_id}.zip"
    try:
        stored_file = await store(
            payload,
            folder="internship-archives",
            filename=stored_name,
            private=True,
            resource_type="raw",
        )
    except StorageError as exc:
        raise HTTPException(
            status_code=502, detail=f"Could not store the archive: {exc}"
        ) from exc

    now = datetime.now(timezone.utc)
    meta = {
        "asset_id": asset_id,
        "filename": filename,
        "size_bytes": len(payload),
        "stored_name": stored_name,
        "storage_key": stored_file.key,
        "storage_backend": stored_file.backend,
        "uploaded_at": now,
    }
    await crud.set_enrollment_fields(db, enrollment_id, {"source_archive": meta})

    return SourceArchiveMeta(
        asset_id=asset_id,
        filename=filename,
        size_bytes=len(payload),
        uploaded_at=now,
        download_url=(
            f"/api/v1/internship/me/enrollments/{enrollment_id}/source-archive"
        ),
    )


@router.get("/me/enrollments/{enrollment_id}/source-archive")
async def download_source_archive(
    enrollment_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    enrollment = await crud.get_enrollment(db, enrollment_id)
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    is_owner = enrollment["user_id"] == str(current_user["_id"])
    is_admin = current_user.get("role") == UserRole.ADMIN.value
    if not (is_owner or is_admin):
        raise HTTPException(status_code=404, detail="Enrollment not found")

    meta = enrollment.get("source_archive")
    if not meta:
        raise HTTPException(status_code=404, detail="No source archive uploaded.")

    key = meta.get("storage_key") or f"internship-archives/{meta.get('stored_name')}"
    backend = meta.get("storage_backend")
    try:
        data = await fetch(key, private=True, resource_type="raw", backend=backend)
    except StorageError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    safe_name = _safe_archive_name(meta.get("filename", "source.zip"))
    return Response(
        content=data,
        media_type="application/zip",
        headers={
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "Cache-Control": "private, max-age=60",
        },
    )


# --------------------------------------------------------------------------
# Certificates
# --------------------------------------------------------------------------

@router.get("/me/certificates", response_model=List[CertificateResponse])
async def my_certificates(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    return await certificate_crud.list_certificates_for_user(db, str(current_user["_id"]))


@router.get("/certificates/verify/{certificate_number}", response_model=CertificateVerification)
async def verify_certificate(
    certificate_number: str, db: AsyncIOMotorDatabase = Depends(get_db)
):
    certificate = await certificate_crud.get_certificate_by_number(db, certificate_number)
    if not certificate:
        raise HTTPException(status_code=404, detail="No certificate with that number")

    return CertificateVerification(
        certificate_number=certificate["certificate_number"],
        recipient_name=certificate["recipient_name"],
        track_title=certificate["track_title"],
        issued_at=certificate["issued_at"],
        valid=not certificate.get("revoked", False),
        revoked=certificate.get("revoked", False),
    )

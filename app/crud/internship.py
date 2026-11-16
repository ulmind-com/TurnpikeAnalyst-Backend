"""Persistence for internship tracks, enrollments and programme settings."""

from __future__ import annotations

import calendar
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.enums import InternshipStatus
from app.schemas.internship import (
    InternshipSettings,
    TrackCreate,
    TrackUpdate,
)

logger = logging.getLogger("uvicorn.error")

SETTINGS_ID = "internship"

# Statuses that mean an attempt is still in flight. Used to stop an intern
# holding several open attempts when the programme does not allow it.
ACTIVE_STATUSES = [
    InternshipStatus.ENROLLED.value,
    InternshipStatus.SUBMITTED.value,
    InternshipStatus.AI_REVIEWING.value,
    InternshipStatus.QUESTIONS_PENDING.value,
    InternshipStatus.UNDER_REVIEW.value,
    InternshipStatus.REVIEW_FAILED.value,
]


def add_months(start: datetime, months: int) -> datetime:
    """Add whole calendar months, clamping to the end of a shorter month.

    Not `30 * months`: an intern who enrols on the 31st of January and is
    told "one month" expects the end of February, and a deadline that drifts
    by a day or two per month is the kind of thing people notice and
    complain about.
    """
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return start.replace(year=year, month=month, day=min(start.day, last_day))


async def ensure_internship_indexes(db: AsyncIOMotorDatabase) -> None:
    await db.internship_tracks.create_index("slug", unique=True)
    await db.internship_enrollments.create_index([("user_id", 1), ("status", 1)])
    await db.internship_enrollments.create_index("track_id")
    await db.internship_enrollments.create_index("deadline_at")

    # One attempt per intern per catalogue track. Partial, because an
    # intern's own project has no track_id and a plain unique index would
    # treat every one of those nulls as the same key and reject the second.
    await db.internship_enrollments.create_index(
        [("user_id", 1), ("track_id", 1)],
        unique=True,
        partialFilterExpression={"track_id": {"$type": "string"}},
        name="uniq_user_track_partial",
    )

    # Drop the pre-partial version of that index if it is still present.
    # Left in place it would reject a second intern-proposed project, since
    # every one of those has track_id null and the old index reads them all
    # as the same key. The partial index above enforces the same rule for
    # catalogue tracks, so nothing is lost.
    existing = await db.internship_enrollments.index_information()
    legacy = existing.get("user_id_1_track_id_1")
    if legacy and legacy.get("unique"):
        await db.internship_enrollments.drop_index("user_id_1_track_id_1")
        logger.info(
            "Dropped legacy unique index user_id_1_track_id_1; "
            "uniq_user_track_partial supersedes it."
        )

    await db.internship_attachments.create_index("enrollment_id")
    await db.internship_attachments.create_index("asset_id", unique=True)


def _public(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {**doc, "_id": str(doc["_id"])}


# --------------------------------------------------------------------------
# Settings
# --------------------------------------------------------------------------

async def get_settings(db: AsyncIOMotorDatabase) -> InternshipSettings:
    doc = await db.internship_settings.find_one({"_id": SETTINGS_ID})
    if not doc:
        return InternshipSettings()
    doc.pop("_id", None)
    return InternshipSettings(**doc)


async def update_settings(
    db: AsyncIOMotorDatabase, changes: Dict[str, Any]
) -> InternshipSettings:
    changes = {key: value for key, value in changes.items() if value is not None}
    changes["updated_at"] = datetime.now(timezone.utc)
    await db.internship_settings.update_one(
        {"_id": SETTINGS_ID}, {"$set": changes}, upsert=True
    )
    return await get_settings(db)


# --------------------------------------------------------------------------
# Tracks
# --------------------------------------------------------------------------

async def list_tracks(
    db: AsyncIOMotorDatabase,
    *,
    published_only: bool = True,
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    query: Dict[str, Any] = {}
    if published_only:
        query["is_published"] = True
    if category:
        query["category"] = category
    cursor = db.internship_tracks.find(query).sort("title", 1).skip(skip).limit(limit)
    return [_public(doc) async for doc in cursor]


async def get_track_by_slug(
    db: AsyncIOMotorDatabase, slug: str, *, published_only: bool = True
) -> Optional[Dict[str, Any]]:
    query: Dict[str, Any] = {"slug": slug}
    if published_only:
        query["is_published"] = True
    doc = await db.internship_tracks.find_one(query)
    return _public(doc) if doc else None


async def get_track(db: AsyncIOMotorDatabase, track_id: str) -> Optional[Dict[str, Any]]:
    if not ObjectId.is_valid(track_id):
        return None
    doc = await db.internship_tracks.find_one({"_id": ObjectId(track_id)})
    return _public(doc) if doc else None


async def create_track(db: AsyncIOMotorDatabase, data: TrackCreate) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    doc = {**data.model_dump(), "created_at": now, "updated_at": now}
    result = await db.internship_tracks.insert_one(doc)
    return {**doc, "_id": str(result.inserted_id)}


async def update_track(
    db: AsyncIOMotorDatabase, track_id: str, data: TrackUpdate
) -> Optional[Dict[str, Any]]:
    if not ObjectId.is_valid(track_id):
        return None
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    if not changes:
        return await get_track(db, track_id)
    changes["updated_at"] = datetime.now(timezone.utc)
    doc = await db.internship_tracks.find_one_and_update(
        {"_id": ObjectId(track_id)}, {"$set": changes}, return_document=True
    )
    return _public(doc) if doc else None


async def delete_track(db: AsyncIOMotorDatabase, track_id: str) -> bool:
    if not ObjectId.is_valid(track_id):
        return False
    result = await db.internship_tracks.delete_one({"_id": ObjectId(track_id)})
    return result.deleted_count == 1


# --------------------------------------------------------------------------
# Enrollments
# --------------------------------------------------------------------------

async def count_active_enrollments(db: AsyncIOMotorDatabase, user_id: str) -> int:
    return await db.internship_enrollments.count_documents(
        {"user_id": user_id, "status": {"$in": ACTIVE_STATUSES}}
    )


async def get_enrollment_for_user_and_track(
    db: AsyncIOMotorDatabase, user_id: str, track_id: str
) -> Optional[Dict[str, Any]]:
    doc = await db.internship_enrollments.find_one(
        {"user_id": user_id, "track_id": track_id}
    )
    return _public(doc) if doc else None


async def create_enrollment(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
    mode: str,
    duration_months: int,
    project_title: str,
    project_summary: Optional[str],
    track: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Open an attempt, from the catalogue or from the intern's own proposal.

    `project_title` is set either way, so every later screen and the
    certificate read one field rather than branching on where the project
    came from.
    """
    now = datetime.now(timezone.utc)
    doc = {
        "user_id": user_id,
        "mode": mode,
        "duration_months": duration_months,
        "project_title": project_title,
        "project_summary": project_summary,
        "track_id": track["_id"] if track else None,
        "track_title": track["title"] if track else None,
        "track_slug": track["slug"] if track else None,
        "status": InternshipStatus.ENROLLED.value,
        "enrolled_at": now,
        "deadline_at": add_months(now, duration_months),
        "submission": None,
        "ai_review": None,
        "questions": [],
        "review_due_at": None,
        "decision": None,
        "certificate_id": None,
    }
    result = await db.internship_enrollments.insert_one(doc)
    return {**doc, "_id": str(result.inserted_id)}


async def get_enrollment(
    db: AsyncIOMotorDatabase, enrollment_id: str
) -> Optional[Dict[str, Any]]:
    if not ObjectId.is_valid(enrollment_id):
        return None
    doc = await db.internship_enrollments.find_one({"_id": ObjectId(enrollment_id)})
    return _public(doc) if doc else None


async def list_enrollments_for_user(
    db: AsyncIOMotorDatabase, user_id: str
) -> List[Dict[str, Any]]:
    cursor = db.internship_enrollments.find({"user_id": user_id}).sort("enrolled_at", -1)
    return [_public(doc) async for doc in cursor]


async def list_enrollments(
    db: AsyncIOMotorDatabase,
    *,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    query: Dict[str, Any] = {}
    if status:
        query["status"] = status
    cursor = (
        db.internship_enrollments.find(query)
        .sort("review_due_at", 1)
        .skip(skip)
        .limit(limit)
    )
    return [_public(doc) async for doc in cursor]


async def set_enrollment_fields(
    db: AsyncIOMotorDatabase, enrollment_id: str, changes: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    if not ObjectId.is_valid(enrollment_id):
        return None
    doc = await db.internship_enrollments.find_one_and_update(
        {"_id": ObjectId(enrollment_id)}, {"$set": changes}, return_document=True
    )
    return _public(doc) if doc else None


# --------------------------------------------------------------------------
# Attachments
# --------------------------------------------------------------------------

async def create_attachment(db: AsyncIOMotorDatabase, doc: Dict[str, Any]) -> Dict[str, Any]:
    result = await db.internship_attachments.insert_one(doc)
    return {**doc, "_id": str(result.inserted_id)}


async def get_attachment(db: AsyncIOMotorDatabase, asset_id: str) -> Optional[Dict[str, Any]]:
    doc = await db.internship_attachments.find_one({"asset_id": asset_id})
    return _public(doc) if doc else None


async def count_attachments(db: AsyncIOMotorDatabase, enrollment_id: str) -> int:
    return await db.internship_attachments.count_documents({"enrollment_id": enrollment_id})


async def expire_overdue_enrollments(db: AsyncIOMotorDatabase) -> int:
    """Mark attempts whose build window closed with nothing submitted.

    Run on startup rather than by a scheduler: the status is only ever read
    when someone looks at an enrollment, so eventual consistency here costs
    nothing and avoids standing up a job runner for one query.
    """
    result = await db.internship_enrollments.update_many(
        {
            "status": InternshipStatus.ENROLLED.value,
            "deadline_at": {"$lt": datetime.now(timezone.utc)},
        },
        {"$set": {"status": InternshipStatus.EXPIRED.value}},
    )
    return result.modified_count

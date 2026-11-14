"""Seed internship project tracks.

Safe to re-run: tracks are matched on slug and updated rather than
duplicated, so editing a brief here and re-running keeps one row per track.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings
from app.models.enums import CourseLevel, TrackCategory

TRACKS = [
    {
        "title": "Document Ingestion Dashboard",
        "slug": "document-ingestion-dashboard",
        "category": TrackCategory.FRONTEND.value,
        "level": CourseLevel.BEGINNER.value,
        "summary": "Build the screen an operations team watches while thousands of documents are being migrated.",
        "brief": (
            "Migration runs are long, and the people responsible for them need one screen that "
            "answers three questions: is it moving, what has failed, and what do I do about it.\n\n"
            "Build that screen against a mock API you design yourself. It should show throughput "
            "over time, a queue of failed documents with the reason for each failure, and a way to "
            "retry a failure without leaving the page.\n\n"
            "We care more about how you handle the unhappy path — an empty queue, a stalled run, a "
            "request that times out — than about how the chart looks."
        ),
        "requirements": [
            "A dashboard showing ingestion throughput over a selectable time range",
            "A failure queue, each row carrying its error reason and a retry action",
            "Explicit loading, empty and error states for every async view",
            "Responsive from 360px upward",
            "A README that lets a stranger run it in under five minutes",
        ],
        "deliverables": [
            "Public GitHub repository",
            "Mock API or fixture data committed alongside the UI",
            "README with setup steps and a short note on your design decisions",
        ],
        "suggested_stack": ["React", "TypeScript", "Any charting library", "Vite or Next.js"],
        "build_days": 30,
        "is_published": True,
    },
    {
        "title": "Retention Policy Service",
        "slug": "retention-policy-service",
        "category": TrackCategory.BACKEND.value,
        "level": CourseLevel.INTERMEDIATE.value,
        "summary": "A service that decides when a document may be deleted — and can prove why.",
        "brief": (
            "Regulated organisations cannot delete a document just because it is old. Retention "
            "depends on the document's class, the date an event occurred, and whether a legal hold "
            "is in force.\n\n"
            "Build an API that stores retention policies, evaluates a document against them, and "
            "returns both the decision and the reasoning behind it. A legal hold must always win "
            "over an expiry.\n\n"
            "The interesting part is the audit trail: six years from now someone has to be able to "
            "ask why a specific document was deleted and get a straight answer."
        ),
        "requirements": [
            "CRUD for retention policies, with validation",
            "An evaluation endpoint returning the decision and the rule that produced it",
            "Legal holds that override expiry, and are themselves auditable",
            "An append-only audit log of every evaluation",
            "Tests covering the hold-versus-expiry conflict",
        ],
        "deliverables": [
            "Public GitHub repository",
            "OpenAPI or equivalent API documentation",
            "Test suite that runs with one command",
        ],
        "suggested_stack": ["FastAPI or Express or Spring Boot", "PostgreSQL or MongoDB", "Docker"],
        "build_days": 30,
        "is_published": True,
    },
    {
        "title": "Invoice Capture Pipeline",
        "slug": "invoice-capture-pipeline",
        "category": TrackCategory.FULLSTACK.value,
        "level": CourseLevel.INTERMEDIATE.value,
        "summary": "Turn a pile of supplier invoices into structured records, and route what the parser gets wrong to a human.",
        "brief": (
            "Suppliers send invoices in every format they feel like. A capture pipeline extracts "
            "the fields that matter, and — this is the part most people skip — hands the ones it is "
            "unsure about to a person.\n\n"
            "Build an upload endpoint, an extraction step, a confidence score per field, and a "
            "review queue where a human corrects low-confidence extractions.\n\n"
            "Extraction can be as simple as regular expressions over text. The exception workflow is "
            "what we are reading your code for."
        ),
        "requirements": [
            "Upload accepting PDF or image invoices",
            "Field extraction with a per-field confidence score",
            "A review queue surfacing only low-confidence extractions",
            "Corrections persisted and visible in the record's history",
            "Sensible handling of a file that cannot be parsed at all",
        ],
        "deliverables": [
            "Public GitHub repository covering both API and UI",
            "Sample invoices committed for reviewers to try",
            "README covering the confidence threshold and why you chose it",
        ],
        "suggested_stack": ["Any backend framework", "React or Vue", "Tesseract or a text parser"],
        "build_days": 45,
        "is_published": True,
    },
    {
        "title": "Migration Reconciliation Report",
        "slug": "migration-reconciliation-report",
        "category": TrackCategory.DATA_ENGINEERING.value,
        "level": CourseLevel.ADVANCED.value,
        "summary": "Prove that everything that left the source system arrived in the target — and show what did not.",
        "brief": (
            "A migration is not finished when the last file copies. It is finished when someone can "
            "show, document by document, that the target holds what the source held.\n\n"
            "Build a reconciliation tool that takes two inventories, matches them, and reports "
            "exactly what is missing, duplicated, or altered. Assume the inventories are large "
            "enough that you cannot hold both in memory.\n\n"
            "Design the output for an auditor, not for a developer."
        ),
        "requirements": [
            "Ingest two inventories in different formats, e.g. CSV and JSON Lines",
            "Match on a configurable key, reporting missing, extra and mismatched rows",
            "Streaming or chunked processing — no loading the whole inventory into memory",
            "A reconciliation report an auditor could read without help",
            "Performance notes: what happens at ten million rows",
        ],
        "deliverables": [
            "Public GitHub repository",
            "A generated sample report committed to the repository",
            "Benchmark showing behaviour on a large synthetic inventory",
        ],
        "suggested_stack": ["Python or Go or Rust", "Any columnar or streaming library"],
        "build_days": 45,
        "is_published": True,
    },
]


async def seed() -> None:
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]

    for track in TRACKS:
        now = datetime.now(timezone.utc)
        existing = await db.internship_tracks.find_one({"slug": track["slug"]})
        if existing:
            await db.internship_tracks.update_one(
                {"_id": existing["_id"]}, {"$set": {**track, "updated_at": now}}
            )
            print(f"Updated track: {track['title']}")
        else:
            await db.internship_tracks.insert_one(
                {**track, "created_at": now, "updated_at": now}
            )
            print(f"Created track: {track['title']}")

    total = await db.internship_tracks.count_documents({})
    print(f"Internship tracks in database: {total}")
    client.close()


if __name__ == "__main__":
    asyncio.run(seed())

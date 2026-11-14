import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import firebase_admin
from firebase_admin import credentials
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.mongodb import db_client, get_db
from app.api.v1.auth import router as auth_router
from app.api.v1.services import router as services_router

from app.api.v1.leads import router as leads_router
from app.api.v1.training import router as training_router
from app.api.v1.blogs import router as blogs_router
from app.api.v1.newsletter import router as newsletter_router
from app.api.v1.content import router as content_router
from app.api.v1.users import router as users_router
from app.api.v1.activity_logs import router as activity_logs_router
from app.api.v1.cms import router as cms_router
from app.api.v1.consultants import router as consultants_router
from app.api.v1.internship import router as internship_router
from app.api.v1.internship_admin import router as internship_admin_router
from app.api.v1.chatbot import router as chatbot_router
from app.api.v1.account import router as account_router
from app.crud.user import ensure_user_indexes
from app.crud.service import ensure_service_indexes

from app.crud.lead import ensure_lead_indexes
from app.crud.training import ensure_training_indexes
from app.crud.blog import ensure_blog_indexes
from app.crud.newsletter import ensure_newsletter_indexes
from app.crud.activity_log import ensure_activity_log_indexes
from app.crud.cms import ensure_cms_indexes
from app.crud.consultant import ensure_consultant_indexes
from app.crud.internship import ensure_internship_indexes, expire_overdue_enrollments
from app.crud.certificate import ensure_certificate_indexes
from app.crud.chatbot import ensure_chatbot_indexes
import logging

logger = logging.getLogger("uvicorn.info")

INDEX_BUILDERS = (
    ensure_user_indexes,
    ensure_service_indexes,
    ensure_lead_indexes,
    ensure_training_indexes,
    ensure_blog_indexes,
    ensure_newsletter_indexes,
    ensure_activity_log_indexes,
    ensure_cms_indexes,
    ensure_consultant_indexes,
    ensure_internship_indexes,
    ensure_certificate_indexes,
    ensure_chatbot_indexes,
)


async def _build_indexes(db) -> None:
    """Ensure every collection's indexes exist.

    Each builder is isolated so one failing collection does not hide the
    others, and so a database that is unreachable at boot degrades to a
    warning rather than preventing the process from serving traffic.
    """
    failed: list[str] = []
    for builder in INDEX_BUILDERS:
        try:
            await builder(db)
        except Exception as exc:
            failed.append(builder.__name__)
            logger.warning("Index setup failed for %s: %s", builder.__name__, exc)
    if failed:
        logger.warning(
            "%d of %d index builders failed. Check that MongoDB at %s is reachable.",
            len(failed),
            len(INDEX_BUILDERS),
            settings.MONGODB_URL,
        )
    else:
        logger.info("All MongoDB collection indexes verified.")


def _init_firebase() -> None:
    """Initialize Google sign-in verification, if it is configured.

    Two sources, because the two environments differ: locally the service
    account sits in a gitignored file, while a platform like Render offers
    environment variables and no filesystem to upload to. When
    FIREBASE_CREDENTIALS_JSON is set it is written to the configured path
    at startup and used from there.

    Absence is a supported configuration: every route except
    /api/v1/auth/google works without it.
    """
    path = settings.FIREBASE_CREDENTIALS_PATH

    if settings.FIREBASE_CREDENTIALS_JSON and not os.path.exists(path):
        try:
            # Parsed first so a malformed value fails here, with a clear
            # message, rather than inside the Firebase SDK later.
            json.loads(settings.FIREBASE_CREDENTIALS_JSON)
            Path(path).write_text(settings.FIREBASE_CREDENTIALS_JSON, encoding="utf-8")
            logger.info("Wrote Firebase credentials from the environment to %s.", path)
        except json.JSONDecodeError as exc:
            logger.error("FIREBASE_CREDENTIALS_JSON is not valid JSON: %s", exc)
            return

    if not os.path.exists(path):
        logger.info(
            "Firebase credentials not found at %s. Google sign-in is disabled; "
            "all other authentication is unaffected.",
            path,
        )
        return
    try:
        firebase_admin.initialize_app(credentials.Certificate(path))
        logger.info("Firebase Admin initialized from %s.", path)
    except Exception as exc:
        logger.error("Firebase credentials at %s could not be loaded: %s", path, exc)


async def _seed_super_admin(db) -> None:
    """Create the first administrator, once.

    This only ever *creates*. If an account with that email already exists
    it is left exactly as it is — otherwise redeploying would silently
    reset a password the owner had since changed from the console, which is
    both surprising and a way to lock someone out of their own platform.
    """
    email = settings.SUPER_ADMIN_EMAIL.strip().lower()
    if not email or not settings.SUPER_ADMIN_PASSWORD:
        return

    from app.core.security import get_password_hash
    from app.models.enums import UserRole

    # Gated on "does ANY administrator exist", not on this specific email.
    # Keying it on the email would mean an owner who changes their sign-in
    # address gets the bootstrap account — and its environment password —
    # recreated on the next restart. That is a permanent backdoor, so the
    # check is about the role, not the address.
    any_admin = await db.users.find_one({"role": UserRole.ADMIN.value})
    if any_admin:
        logger.info(
            "An administrator already exists; SUPER_ADMIN_* is a bootstrap and is ignored."
        )
        return

    await db.users.insert_one(
        {
            "full_name": settings.SUPER_ADMIN_NAME,
            "email": email,
            "hashed_password": get_password_hash(settings.SUPER_ADMIN_PASSWORD),
            "role": UserRole.ADMIN.value,
            "is_active": True,
            "theme": "light",
            "created_at": datetime.now(timezone.utc),
        }
    )
    logger.warning(
        "Created the first administrator (%s) from SUPER_ADMIN_EMAIL. "
        "Change the password from the console; the environment value is a "
        "bootstrap, not the live credential.",
        email,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.secret_key_is_insecure_default:
        logger.warning(
            "SECRET_KEY is the built-in development default. Tokens signed with "
            "it are forgeable. Set SECRET_KEY in the environment before exposing "
            "this API to anyone."
        )

    db_client.connect_db()
    await _build_indexes(get_db())
    _init_firebase()

    try:
        await _seed_super_admin(get_db())
    except Exception as exc:  # noqa: BLE001 — never block startup on seeding
        logger.warning("Could not seed the first administrator: %s", exc)

    # Attempts whose build window closed with nothing submitted are settled
    # here rather than by a scheduler: the status is only read when someone
    # opens an enrollment, so doing it at boot is enough and keeps the
    # deployment to a single process.
    try:
        expired = await expire_overdue_enrollments(get_db())
        if expired:
            logger.info("Marked %d internship attempt(s) as expired.", expired)
    except Exception as exc:  # noqa: BLE001 — never block startup on bookkeeping
        logger.warning("Could not settle expired internship attempts: %s", exc)

    yield

    db_client.close_db()

app = FastAPI(
    title="Turnpike Analyst Enterprise Platform API",
    description="Production-ready RESTful API backend for Turnpike Analyst covering ECM migrations (JAMES WEBB Server), AI Agent tools (Agent P8), training courses, consultations, CMS/blogging, lead capture, and role-based administration.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# The API answers credentialed requests, so the allowed origins stay an
# explicit list from configuration. A wildcard here would let any site issue
# authenticated requests on a signed-in user's behalf.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Api-Key"],
)

# Mount domain endpoint routers under /api/v1 prefix
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication & Token Security"])
app.include_router(services_router, prefix="/api/v1/services", tags=["Enterprise Services Catalog"])

app.include_router(leads_router, prefix="/api/v1/leads", tags=["Leads & Consultation Scheduling"])
app.include_router(training_router, prefix="/api/v1/training", tags=["Training & Academy"])
app.include_router(blogs_router, prefix="/api/v1/blogs", tags=["Blog & CMS"])
app.include_router(newsletter_router, prefix="/api/v1/newsletter", tags=["Newsletter Subscriptions"])
app.include_router(content_router, prefix="/api/v1/content", tags=["Dynamic Content"])
app.include_router(users_router, prefix="/api/v1/users", tags=["User Management"])
app.include_router(activity_logs_router, prefix="/api/v1/activity-logs", tags=["Activity Logs"])
app.include_router(cms_router, prefix="/api/v1/cms", tags=["CMS Assets"])
app.include_router(consultants_router, prefix="/api/v1/consultants", tags=["Consultants"])
app.include_router(internship_router, prefix="/api/v1/internship", tags=["Internship Programme"])
app.include_router(
    internship_admin_router,
    prefix="/api/v1/internship/admin",
    tags=["Internship Administration"],
)
app.include_router(chatbot_router, prefix="/api/v1/chatbot", tags=["Support Chatbot"])
app.include_router(account_router, prefix="/api/v1/account", tags=["Administrator Account"])

# Certificate backgrounds and rendered PDFs. Served read-only; nothing here
# is user-generated beyond what an admin uploaded.
_upload_root = Path(settings.UPLOAD_DIR)
_upload_root.mkdir(parents=True, exist_ok=True)
(_upload_root / "certificates").mkdir(exist_ok=True)
(_upload_root / "certificate-templates").mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_upload_root)), name="uploads")

@app.get("/", tags=["System Health Check"])
async def root_health_check():
    return {
        "status": "online",
        "portal": "Turnpike Analyst Enterprise Platform Backend",
        "documentation_swagger": "/docs",
        "documentation_redoc": "/redoc",
        "version": "1.0.0",
        "architecture": "Async FastAPI + MongoDB Motor + Pydantic v2"
    }

"""Where uploaded and generated files live.

Render runs the API on an ephemeral filesystem: anything written to disk is
gone at the next deploy, and a certificate that disappears a week after it
was issued is worse than one that was never generated. So when Cloudinary
is configured, files go there; when it is not — or when a source archive
exceeds Cloudinary's 10 MB raw free-tier limit — they go to disk, and the two
behave the same to callers.

Two visibilities, and the difference matters:

* **public** — certificate PDFs and template artwork. Served from
  Cloudinary's CDN by URL. The URLs are unguessable, which is the same
  model the local static mount already used.
* **private** — intern-uploaded diagrams and source archives. Uploaded with
  `type: "authenticated"` so Cloudinary will not serve them from a plain URL;
  the API streams them through its own ownership check instead.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger("uvicorn.error")

# Cloudinary free-tier hard cap for raw files (10 MiB = 10,485,760 bytes).
CLOUDINARY_RAW_MAX_BYTES = 10 * 1024 * 1024


class StorageError(RuntimeError):
    """A file could not be stored, fetched, or deleted."""


@dataclass(frozen=True)
class StoredFile:
    """Where a file ended up, in terms the callers can persist."""

    # Cloudinary public_id, an S3 object key, or a path relative to the upload
    # root on disk.
    key: str
    # Set only for public files; None for private ones, which are streamed.
    url: Optional[str]
    backend: str  # "cloudinary" | "s3" | "local"


# --------------------------------------------------------------------------
# S3-compatible storage (Supabase Storage, Cloudflare R2, MinIO, …)
# --------------------------------------------------------------------------

def using_s3() -> bool:
    return settings.archive_s3_configured


def _is_s3_key(backend: Optional[str]) -> bool:
    return backend == "s3"


@lru_cache(maxsize=1)
def _s3_client():
    """A cached boto3 S3 client for the configured S3-compatible endpoint.

    Path-style addressing is required by Supabase Storage (and is harmless for
    R2/MinIO). The client is thread-safe, so one instance is reused and every
    call runs in a worker thread off the event loop.
    """
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=settings.ARCHIVE_S3_ENDPOINT,
        aws_access_key_id=settings.ARCHIVE_S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.ARCHIVE_S3_SECRET_ACCESS_KEY,
        region_name=settings.ARCHIVE_S3_REGION or "auto",
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            retries={"max_attempts": 3},
        ),
    )


async def _store_s3(data: bytes, *, folder: str, stem: str, suffix: str) -> "StoredFile":
    key = f"turnpike/{folder}/{stem}{suffix}"

    def put() -> None:
        _s3_client().put_object(Bucket=settings.ARCHIVE_S3_BUCKET, Key=key, Body=data)

    try:
        await asyncio.to_thread(put)
    except Exception as exc:  # noqa: BLE001
        raise StorageError(f"S3 upload failed: {exc}") from exc
    # Private: no public URL; the API streams the bytes through its own check.
    return StoredFile(key=key, url=None, backend="s3")


async def _fetch_s3(key: str) -> bytes:
    def get() -> bytes:
        resp = _s3_client().get_object(Bucket=settings.ARCHIVE_S3_BUCKET, Key=key)
        return resp["Body"].read()

    try:
        return await asyncio.to_thread(get)
    except Exception as exc:  # noqa: BLE001
        raise StorageError(f"File not found in S3: {key} ({exc})") from exc


async def _delete_s3(key: str) -> bool:
    # S3 delete_object is idempotent — deleting an absent key is not an error.
    def destroy() -> None:
        _s3_client().delete_object(Bucket=settings.ARCHIVE_S3_BUCKET, Key=key)

    try:
        await asyncio.to_thread(destroy)
        return True
    except Exception as exc:  # noqa: BLE001
        raise StorageError(f"S3 delete failed: {exc}") from exc


def _configure_cloudinary() -> None:
    import cloudinary

    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )


def using_cloudinary() -> bool:
    return settings.cloudinary_configured


def _is_cloudinary_key(key: str, backend: Optional[str] = None) -> bool:
    if backend == "cloudinary":
        return using_cloudinary()
    if backend == "local":
        return False
    return (
        using_cloudinary()
        and not key.startswith(("uploads/", "private_uploads/"))
        and key.startswith("turnpike/")
    )


def _resolve_local_path(key: str, *, private: bool) -> Path:
    root = Path(settings.PRIVATE_UPLOAD_DIR if private else settings.UPLOAD_DIR).resolve()
    clean_key = key.lstrip("/")
    for prefix in (Path(settings.PRIVATE_UPLOAD_DIR).name, Path(settings.UPLOAD_DIR).name, "private_uploads", "uploads"):
        if clean_key.startswith(f"{prefix}/"):
            clean_key = clean_key.split("/", 1)[1]
            break
    path = (root / clean_key).resolve()
    if not path.is_relative_to(root):
        raise StorageError("Refusing to access outside the upload directories.")
    return path


# --------------------------------------------------------------------------
# Writing
# --------------------------------------------------------------------------

async def store(
    data: bytes,
    *,
    folder: str,
    filename: str,
    private: bool,
    resource_type: str = "image",
) -> StoredFile:
    """Store bytes and report where they went.

    `filename` is used as the identifier, not as a path: callers already
    generate unguessable names, and letting a caller-supplied name reach a
    filesystem path is how directory traversal happens.
    """
    stem = Path(filename).stem
    suffix = Path(filename).suffix

    # Project source archives go to S3-compatible storage when it is configured
    # (Cloudinary's raw free tier caps a file at 10 MB, and Render's disk is
    # ephemeral). Scoped to the archive folder so certificate PDFs and diagram
    # images keep their existing Cloudinary/local behaviour.
    if using_s3() and resource_type == "raw" and private and folder == "internship-archives":
        logger.info("Storing source archive (%d bytes) to S3", len(data))
        return await _store_s3(data, folder=folder, stem=stem, suffix=suffix)

    should_try_cloudinary = using_cloudinary() and not (
        resource_type == "raw" and len(data) > CLOUDINARY_RAW_MAX_BYTES
    )

    if should_try_cloudinary:
        import cloudinary.uploader

        _configure_cloudinary()
        # Cloudinary raw resources treat the extension as part of the public_id.
        public_id = (
            f"turnpike/{folder}/{stem}{suffix}"
            if resource_type == "raw"
            else f"turnpike/{folder}/{stem}"
        )

        def upload() -> dict:
            return cloudinary.uploader.upload(
                data,
                public_id=public_id,
                resource_type=resource_type,
                # "authenticated" means a bare URL will not serve it, which
                # is what keeps intern uploads behind our ownership check.
                type="authenticated" if private else "upload",
                overwrite=True,
                invalidate=True,
            )

        try:
            # The SDK is synchronous; a worker thread keeps it off the loop.
            result = await asyncio.to_thread(upload)
            return StoredFile(
                key=result["public_id"],
                url=None if private else result.get("secure_url"),
                backend="cloudinary",
            )
        except Exception as exc:
            msg = str(exc).lower()
            if resource_type == "raw" and ("too large" in msg or "maximum" in msg):
                logger.warning(
                    "Cloudinary raw limit exceeded (%d bytes); falling back to local storage",
                    len(data),
                )
            else:
                raise StorageError(f"Cloudinary upload failed: {exc}") from exc
    elif using_cloudinary() and resource_type == "raw" and len(data) > CLOUDINARY_RAW_MAX_BYTES:
        logger.warning(
            "Raw payload %d bytes exceeds Cloudinary 10 MB limit; using local storage",
            len(data),
        )

    root = Path(settings.PRIVATE_UPLOAD_DIR if private else settings.UPLOAD_DIR) / folder
    root.mkdir(parents=True, exist_ok=True)
    (root / f"{stem}{suffix}").write_bytes(data)
    return StoredFile(
        key=f"{folder}/{stem}{suffix}",
        url=None if private else f"/uploads/{folder}/{stem}{suffix}",
        backend="local",
    )


# --------------------------------------------------------------------------
# Reading
# --------------------------------------------------------------------------

async def fetch(
    key: str,
    *,
    private: bool,
    resource_type: str = "image",
    backend: Optional[str] = None,
) -> bytes:
    """Read a stored file back, whichever backend holds it."""
    if _is_s3_key(backend):
        return await _fetch_s3(key)

    if _is_cloudinary_key(key, backend):
        import cloudinary.utils
        import httpx

        _configure_cloudinary()
        url, _ = cloudinary.utils.cloudinary_url(
            key,
            resource_type=resource_type,
            type="authenticated" if private else "upload",
            # A short-lived signature, so the URL cannot be shared onward.
            sign_url=private,
        )
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
        if response.status_code != 200:
            raise StorageError(f"Cloudinary returned {response.status_code} for {key}")
        return response.content

    path = _resolve_local_path(key, private=private)
    if not path.exists():
        raise StorageError(f"File not found: {key}")
    return path.read_bytes()


# --------------------------------------------------------------------------
# Deleting
# --------------------------------------------------------------------------

async def delete_file(
    key: str,
    *,
    private: bool,
    resource_type: str = "image",
    backend: Optional[str] = None,
) -> bool:
    """Delete a stored file from Cloudinary or local disk.

    Returns True if the asset was deleted or was already absent.
    """
    if _is_s3_key(backend):
        return await _delete_s3(key)

    if _is_cloudinary_key(key, backend):
        import cloudinary.uploader

        _configure_cloudinary()

        def destroy() -> dict:
            return cloudinary.uploader.destroy(
                key,
                resource_type=resource_type,
                type="authenticated" if private else "upload",
                invalidate=True,
            )

        try:
            result = await asyncio.to_thread(destroy)
            return result.get("result") in {"ok", "not found"}
        except Exception as exc:
            raise StorageError(f"Cloudinary delete failed: {exc}") from exc

    path = _resolve_local_path(key, private=private)
    if path.exists():
        path.unlink()
    return True

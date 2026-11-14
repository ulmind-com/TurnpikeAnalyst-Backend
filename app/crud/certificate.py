"""Persistence for certificate templates and issued certificates."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.certificate import CertificateTemplateCreate, CertificateTemplateUpdate


async def ensure_certificate_indexes(db: AsyncIOMotorDatabase) -> None:
    await db.certificates.create_index("certificate_number", unique=True)
    await db.certificates.create_index("user_id")
    await db.certificates.create_index("enrollment_id", unique=True)
    await db.certificate_templates.create_index("is_active")


def _public(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {**doc, "_id": str(doc["_id"])}


# --------------------------------------------------------------------------
# Templates
# --------------------------------------------------------------------------

async def list_templates(db: AsyncIOMotorDatabase) -> List[Dict[str, Any]]:
    cursor = db.certificate_templates.find().sort("created_at", -1)
    return [_public(doc) async for doc in cursor]


async def get_template(db: AsyncIOMotorDatabase, template_id: str) -> Optional[Dict[str, Any]]:
    if not ObjectId.is_valid(template_id):
        return None
    doc = await db.certificate_templates.find_one({"_id": ObjectId(template_id)})
    return _public(doc) if doc else None


async def get_active_template(db: AsyncIOMotorDatabase) -> Optional[Dict[str, Any]]:
    doc = await db.certificate_templates.find_one({"is_active": True})
    return _public(doc) if doc else None


async def create_template(
    db: AsyncIOMotorDatabase, data: CertificateTemplateCreate
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    doc = {**data.model_dump(), "created_at": now, "updated_at": now}
    result = await db.certificate_templates.insert_one(doc)
    created = {**doc, "_id": str(result.inserted_id)}
    if doc.get("is_active"):
        await _deactivate_others(db, created["_id"])
    return created


async def update_template(
    db: AsyncIOMotorDatabase, template_id: str, data: CertificateTemplateUpdate
) -> Optional[Dict[str, Any]]:
    if not ObjectId.is_valid(template_id):
        return None
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    if not changes:
        return await get_template(db, template_id)
    changes["updated_at"] = datetime.now(timezone.utc)
    doc = await db.certificate_templates.find_one_and_update(
        {"_id": ObjectId(template_id)}, {"$set": changes}, return_document=True
    )
    if doc and changes.get("is_active"):
        await _deactivate_others(db, str(doc["_id"]))
    return _public(doc) if doc else None


async def _deactivate_others(db: AsyncIOMotorDatabase, template_id: str) -> None:
    """Exactly one template is active at a time, so certificate issuing never
    has to choose between candidates."""
    await db.certificate_templates.update_many(
        {"_id": {"$ne": ObjectId(template_id)}}, {"$set": {"is_active": False}}
    )


async def delete_template(db: AsyncIOMotorDatabase, template_id: str) -> bool:
    if not ObjectId.is_valid(template_id):
        return False
    result = await db.certificate_templates.delete_one({"_id": ObjectId(template_id)})
    return result.deleted_count == 1


# --------------------------------------------------------------------------
# Issued certificates
# --------------------------------------------------------------------------

async def create_certificate(db: AsyncIOMotorDatabase, doc: Dict[str, Any]) -> Dict[str, Any]:
    result = await db.certificates.insert_one(doc)
    return {**doc, "_id": str(result.inserted_id)}


async def get_certificate(db: AsyncIOMotorDatabase, certificate_id: str) -> Optional[Dict[str, Any]]:
    if not ObjectId.is_valid(certificate_id):
        return None
    doc = await db.certificates.find_one({"_id": ObjectId(certificate_id)})
    return _public(doc) if doc else None


async def get_certificate_by_number(
    db: AsyncIOMotorDatabase, number: str
) -> Optional[Dict[str, Any]]:
    doc = await db.certificates.find_one({"certificate_number": number})
    return _public(doc) if doc else None


async def list_certificates_for_user(
    db: AsyncIOMotorDatabase, user_id: str
) -> List[Dict[str, Any]]:
    cursor = db.certificates.find({"user_id": user_id}).sort("issued_at", -1)
    return [_public(doc) async for doc in cursor]


async def revoke_certificate(
    db: AsyncIOMotorDatabase, certificate_id: str, reason: str
) -> Optional[Dict[str, Any]]:
    if not ObjectId.is_valid(certificate_id):
        return None
    doc = await db.certificates.find_one_and_update(
        {"_id": ObjectId(certificate_id)},
        {"$set": {"revoked": True, "revoked_reason": reason}},
        return_document=True,
    )
    return _public(doc) if doc else None

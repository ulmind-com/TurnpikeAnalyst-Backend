"""The signed-in administrator's own credentials.

Separate from the user-management routes on purpose. Those are an admin
acting on *other* accounts; these are an admin acting on their own, and the
rules differ: changing your own email or password requires re-entering the
current password, and nothing here can change a role.

The first administrator is seeded from the environment at startup (see
`app.main`), so a fresh deployment has a way in. From then on the account
is managed here — the environment value is a bootstrap, not the source of
truth.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import EmailStr, Field

from app.api.deps import get_current_admin
from app.core.security import get_password_hash, verify_password
from app.crud.user import get_user_by_email
from app.db.mongodb import get_db
from app.schemas.common import BaseSchema
from app.schemas.user import UserResponse

logger = logging.getLogger("uvicorn.error")
router = APIRouter()


class CredentialChange(BaseSchema):
    """Change the signed-in admin's email, password, or both."""

    # Always required. Without it, anyone who finds an unattended signed-in
    # console could lock the real owner out of their own account.
    current_password: str = Field(..., min_length=1)
    new_email: EmailStr | None = None
    new_password: str | None = Field(
        None,
        min_length=10,
        description="At least 10 characters. This account can approve certificates.",
    )
    full_name: str | None = Field(None, min_length=2, max_length=100)


@router.get("/me", response_model=UserResponse)
async def read_me(current_admin: Dict[str, Any] = Depends(get_current_admin)):
    return current_admin


@router.post("/credentials", response_model=UserResponse)
async def change_credentials(
    payload: CredentialChange,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_admin: Dict[str, Any] = Depends(get_current_admin),
):
    """Change your own sign-in details.

    Deliberately narrow: email, password and display name only. Role and
    active status are not settable here, so this endpoint cannot be used to
    escalate anything — only to move an existing admin account onto
    different credentials.
    """
    if not payload.new_email and not payload.new_password and not payload.full_name:
        raise HTTPException(status_code=422, detail="Nothing to change.")

    stored_hash = current_admin.get("hashed_password")
    if not stored_hash or not verify_password(payload.current_password, stored_hash):
        # Same message whichever part is wrong, so this cannot be used to
        # probe which accounts exist or which passwords are close.
        raise HTTPException(status_code=403, detail="Current password is incorrect.")

    changes: Dict[str, Any] = {"updated_at": datetime.now(timezone.utc)}

    if payload.new_email and payload.new_email.lower() != current_admin["email"].lower():
        clash = await get_user_by_email(db, payload.new_email)
        if clash:
            raise HTTPException(status_code=409, detail="That email is already in use.")
        changes["email"] = payload.new_email

    if payload.new_password:
        if payload.new_password == payload.current_password:
            raise HTTPException(
                status_code=422, detail="The new password must differ from the current one."
            )
        changes["hashed_password"] = get_password_hash(payload.new_password)

    if payload.full_name:
        changes["full_name"] = payload.full_name

    await db.users.update_one({"_id": ObjectId(str(current_admin["_id"]))}, {"$set": changes})

    logger.info(
        "Admin %s changed their own credentials (%s).",
        current_admin["email"],
        ", ".join(k for k in changes if k != "updated_at") or "no fields",
    )

    updated = await db.users.find_one({"_id": ObjectId(str(current_admin["_id"]))})
    return updated

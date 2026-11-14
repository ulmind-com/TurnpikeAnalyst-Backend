"""Read/write the singleton homepage content document.

Stored in `site_content` with a fixed string `_id` so there is exactly one
homepage. Reads merge the stored document over the schema defaults, so missing
or newly-added fields always resolve to a renderable value.
"""

from typing import Any, Dict
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.homepage import HomepageContent, HomepageUpdate

HOMEPAGE_ID = "homepage"
COLLECTION = "site_content"


async def get_homepage(db: AsyncIOMotorDatabase) -> Dict[str, Any]:
    """Return the homepage content, filled out with defaults for any gaps."""
    stored = await db[COLLECTION].find_one({"_id": HOMEPAGE_ID}) or {}
    stored.pop("_id", None)
    stored.pop("updated_at", None)
    # Round-trip through the schema so defaults fill every absent field and
    # unknown legacy keys are dropped.
    return HomepageContent(**stored).model_dump()


async def set_homepage(db: AsyncIOMotorDatabase, data: HomepageUpdate) -> Dict[str, Any]:
    """Replace the homepage document wholesale (upsert)."""
    doc = data.model_dump()
    await db[COLLECTION].update_one(
        {"_id": HOMEPAGE_ID},
        {"$set": doc},
        upsert=True,
    )
    return doc

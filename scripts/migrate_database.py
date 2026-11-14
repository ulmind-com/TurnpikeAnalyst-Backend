"""Copy one MongoDB database into another.

Used to move off the old cluster onto the new one. Written to be safe to
re-run and safe to abort:

* Nothing is deleted. Documents are upserted on `_id`, so a second run
  updates rather than duplicates, and an interrupted run can simply be
  repeated.
* The target is never emptied. If a collection already holds documents the
  source does not, they stay — a migration should not be able to destroy
  data that only exists on the destination.
* `--dry-run` reports exactly what would be copied and writes nothing.

    python -m scripts.migrate_database --dry-run
    python -m scripts.migrate_database
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from typing import Any, Dict, List

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import UpdateOne

from app.core.config import settings

BATCH = 500


def redact(uri: str) -> str:
    import re

    return re.sub(r"://[^:/@]+:[^@]+@", "://***:***@", uri)


async def copy_collection(source_db, target_db, name: str, dry_run: bool) -> Dict[str, int]:
    total = await source_db[name].count_documents({})
    if total == 0:
        return {"read": 0, "written": 0}

    written = 0
    batch: List[UpdateOne] = []

    async for doc in source_db[name].find({}):
        # Upsert on the source _id so re-running converges instead of
        # duplicating, and so ObjectId references between collections
        # (enrollment -> user, certificate -> enrollment) stay valid.
        batch.append(UpdateOne({"_id": doc["_id"]}, {"$set": doc}, upsert=True))
        if len(batch) >= BATCH:
            if not dry_run:
                await target_db[name].bulk_write(batch, ordered=False)
            written += len(batch)
            batch = []

    if batch:
        if not dry_run:
            await target_db[name].bulk_write(batch, ordered=False)
        written += len(batch)

    return {"read": total, "written": written}


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        default=os.getenv("MIGRATE_SOURCE_URL", ""),
        help="Source connection string. Defaults to $MIGRATE_SOURCE_URL.",
    )
    parser.add_argument(
        "--target",
        default=settings.MONGODB_URL,
        help="Target connection string. Defaults to the configured MONGODB_URL.",
    )
    parser.add_argument("--database", default=settings.DATABASE_NAME)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.source:
        parser.error("No source given. Pass --source or set MIGRATE_SOURCE_URL.")
    if args.source == args.target:
        parser.error("Source and target are the same cluster.")

    source_client = AsyncIOMotorClient(args.source, serverSelectionTimeoutMS=20000)
    target_client = AsyncIOMotorClient(args.target, serverSelectionTimeoutMS=20000)
    source_db = source_client[args.database]
    target_db = target_client[args.database]

    print(f"source : {redact(args.source)}  db={args.database}")
    print(f"target : {redact(args.target)}  db={args.database}")
    print("mode   :", "DRY RUN — nothing will be written" if args.dry_run else "WRITING")
    print()

    names = sorted(await source_db.list_collection_names())
    totals = {"read": 0, "written": 0}
    widest = max((len(n) for n in names), default=10)

    for name in names:
        before = await target_db[name].count_documents({})
        stats = await copy_collection(source_db, target_db, name, args.dry_run)
        after = before if args.dry_run else await target_db[name].count_documents({})
        totals["read"] += stats["read"]
        totals["written"] += stats["written"]
        print(
            f"  {name:<{widest}}  source={stats['read']:>5}  "
            f"target {before:>5} -> {after:>5}"
        )

    print()
    print(f"read {totals['read']} documents, wrote {totals['written']}")
    if args.dry_run:
        print("Dry run: nothing was written. Re-run without --dry-run to apply.")

    source_client.close()
    target_client.close()


if __name__ == "__main__":
    asyncio.run(main())

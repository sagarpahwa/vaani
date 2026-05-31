#!/usr/bin/env python3
"""Seed the POC mock MongoDB with demo users, learner profiles, and guided scripts.

Idempotent: upserts keyed on each collection's natural key. Targets ONLY the
isolated mock DB (guarded by `assert_mock_target`).

Usage:
    python3 -m services.api.db.seed_mock
"""

import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from .init_mock_db import assert_mock_target

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("seed_mock")

SCHEMA_VERSION = "1.0"
SEED_DIR = Path(__file__).parent / "seed_data"

# (seed file, collection name, natural upsert key)
SEED_SPECS = [
    ("users.json", "users", "user_id"),
    ("learner_profiles.json", "learner_profiles", "user_id"),
    ("guided_scripts.json", "guided_scripts", "script_id"),
]


def load_json(path: Path) -> list:
    return json.loads(path.read_text(encoding="utf-8"))


def upsert_docs(
    collection, records: list, key_field: str, now: datetime | None = None
) -> tuple[int, int]:
    """Upsert records by `key_field`. Returns (inserted, modified).

    Sets `updated_at`/`schema_version` on every write and `created_at` only on
    insert, matching the repo's core data-model rules. Uses per-document
    `update_one` (not `bulk_write`) for portability across the mock backend.
    """
    now = now or datetime.now(UTC)
    inserted = modified = 0
    for rec in records:
        doc = {**rec, "updated_at": now, "schema_version": SCHEMA_VERSION}
        result = collection.update_one(
            {key_field: rec[key_field]},
            {"$set": doc, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        if result.upserted_id is not None:
            inserted += 1
        elif result.modified_count:
            modified += 1
    return inserted, modified


def seed_all(db, seed_dir: Path = SEED_DIR, now: datetime | None = None) -> dict:
    """Seed every collection from its seed file. Returns {collection: (ins, upd)}."""
    now = now or datetime.now(UTC)
    summary = {}
    for filename, collection_name, key_field in SEED_SPECS:
        records = load_json(seed_dir / filename)
        summary[collection_name] = upsert_docs(db[collection_name], records, key_field, now=now)
    return summary


def main():  # pragma: no cover
    from ..config import get_settings

    settings = get_settings()
    assert_mock_target(settings.poc_mongo_uri, settings.poc_mongo_db)

    log.info(
        "Connecting to mock MongoDB at %s (DB: %s)", settings.poc_mongo_uri, settings.poc_mongo_db
    )
    client = MongoClient(settings.poc_mongo_uri, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
    except Exception as e:
        log.error("Cannot connect to mock MongoDB: %s", e)
        log.error("Is it up? Run: make poc-db-up && make poc-db-setup")
        sys.exit(1)

    db = client[settings.poc_mongo_db]
    try:
        summary = seed_all(db)
    except PyMongoError as e:
        log.error("Seeding failed: %s", e)
        sys.exit(1)

    for collection_name, (ins, upd) in summary.items():
        log.info("  ✓ %s: %d inserted, %d updated", collection_name, ins, upd)
    log.info("Mock DB seeding complete.")
    client.close()


if __name__ == "__main__":
    main()

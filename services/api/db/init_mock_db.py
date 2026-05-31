#!/usr/bin/env python3
"""Initialize the POC mock MongoDB: collections + JSON Schema validators + indexes.

Idempotent and safe to re-run. Targets ONLY the isolated mock DB (`*_mock` on
:27018). The `assert_mock_target` guard refuses to run against the real DB.

Usage:
    python3 -m services.api.db.init_mock_db
"""

import json
import logging
import sys
from pathlib import Path

from pymongo import MongoClient
from pymongo.errors import PyMongoError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("init_mock_db")

SCHEMAS_DIR = Path(__file__).parent / "schemas"

# name == schema filename (schemas/<name>.json) == collection name.
# `unique` is the natural upsert key; `indexes` are additional secondary indexes.
COLLECTION_SPECS = [
    {"name": "users", "unique": [("user_id", 1)], "indexes": []},
    {"name": "learner_profiles", "unique": [("user_id", 1)], "indexes": []},
    {"name": "guided_scripts", "unique": [("script_id", 1)], "indexes": [[("language", 1)]]},
    {
        "name": "practice_sessions",
        "unique": [("session_id", 1)],
        "indexes": [[("user_id", 1), ("created_at", -1)], [("status", 1)]],
    },
    {
        "name": "session_utterances",
        "unique": [("utterance_id", 1)],
        "indexes": [[("session_id", 1), ("line_index", 1)]],
    },
    {"name": "coaching_feedback", "unique": [("feedback_id", 1)], "indexes": [[("session_id", 1)]]},
    {
        "name": "audio_corrections",
        "unique": [("correction_id", 1)],
        "indexes": [[("session_id", 1)]],
    },
    {
        "name": "progress_snapshots",
        "unique": [("snapshot_id", 1)],
        "indexes": [[("user_id", 1), ("created_at", -1)]],
    },
    {
        "name": "model_eval_runs",
        "unique": [("run_id", 1)],
        "indexes": [[("scoring_model_version", 1)]],
    },
    {
        "name": "release_health_events",
        "unique": [("event_id", 1)],
        "indexes": [[("event_type", 1), ("created_at", -1)]],
    },
]


def assert_mock_target(mongo_uri: str, mongo_db: str) -> None:
    """Refuse to operate on anything but the isolated mock DB.

    Hard isolation guard: the POC must never touch the real
    `public_speaking_intelligence` database (port 27017).
    """
    if not mongo_db.endswith("_mock"):
        raise RuntimeError(
            f"Refusing to run: target DB {mongo_db!r} is not a '*_mock' database. "
            "The POC may only write to the isolated mock DB."
        )
    if ":27017" in mongo_uri or ":27017/" in mongo_uri:
        raise RuntimeError(
            "Refusing to run: Mongo URI points at port 27017 (the real DB). "
            "The POC mock DB runs on port 27018."
        )


def load_schema(name: str) -> dict:
    path = SCHEMAS_DIR / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_collection(db, name: str) -> bool:
    """Create the collection if absent. Returns True if created, False if it existed."""
    if name in db.list_collection_names():
        return False
    db.create_collection(name)
    return True


def apply_validator(db, name: str, schema: dict) -> bool:
    """Attach a JSON Schema validator to an existing collection (best-effort).

    Real MongoDB enforces this; mongomock does not support collMod and will
    raise, in which case validation is simply skipped (acceptable for tests).
    """
    try:
        db.command("collMod", name, validator=schema, validationLevel="moderate")
        return True
    except (PyMongoError, NotImplementedError, TypeError) as e:
        log.debug("validator not applied for %s (mock backend?): %s", name, e)
        return False


def ensure_indexes(db, name: str, unique, indexes) -> int:
    count = 0
    if unique:
        db[name].create_index(unique, unique=True)
        count += 1
    for keys in indexes or []:
        db[name].create_index(keys)
        count += 1
    return count


def init_db(db, apply_validators: bool = True) -> dict:
    """Create all POC collections (+validators +indexes). Idempotent."""
    created, existing = [], []
    index_count = 0
    for spec in COLLECTION_SPECS:
        name = spec["name"]
        if ensure_collection(db, name):
            created.append(name)
        else:
            existing.append(name)
        if apply_validators:
            apply_validator(db, name, load_schema(name))
        index_count += ensure_indexes(db, name, spec.get("unique"), spec.get("indexes"))
    return {"created": created, "existing": existing, "indexes": index_count}


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
        log.error("Is it up? Run: make poc-db-up")
        sys.exit(1)

    db = client[settings.poc_mongo_db]
    summary = init_db(db)

    log.info("  ✓ collections created: %s", summary["created"] or "(none — all existed)")
    log.info("  ✓ collections existing: %s", summary["existing"] or "(none)")
    log.info("  ✓ indexes ensured: %d", summary["indexes"])
    log.info("Mock DB init complete (%d collections).", len(COLLECTION_SPECS))
    client.close()


if __name__ == "__main__":
    main()

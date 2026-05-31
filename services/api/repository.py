"""Persistence helpers for the coaching collections (mock DB).

Thin module-level functions over PyMongo collections, mirroring the repo's
core data-model rules: `created_at` set once via `$setOnInsert`, `updated_at`
and `schema_version` on every write. Per-document `update_one` (not bulk) keeps
these portable across mongomock and real Mongo.
"""

from datetime import UTC, datetime

SCHEMA_VERSION = "1.0"


def _now() -> datetime:
    return datetime.now(UTC)


def _upsert(collection, key_field: str, doc: dict, now: datetime | None = None) -> dict:
    now = now or _now()
    payload = {**doc, "updated_at": now, "schema_version": SCHEMA_VERSION}
    collection.update_one(
        {key_field: doc[key_field]},
        {"$set": payload, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    return collection.find_one({key_field: doc[key_field]}, {"_id": 0})


# ---- guided scripts (read-only here; seeded separately) --------------------


def list_scripts(db) -> list[dict]:
    return list(db.guided_scripts.find({}, {"_id": 0}).sort("script_id", 1))


def get_script(db, script_id: str) -> dict | None:
    return db.guided_scripts.find_one({"script_id": script_id}, {"_id": 0})


# ---- sessions --------------------------------------------------------------


def create_session(db, doc: dict) -> dict:
    return _upsert(db.practice_sessions, "session_id", doc)


def get_session(db, session_id: str) -> dict | None:
    return db.practice_sessions.find_one({"session_id": session_id}, {"_id": 0})


def update_session(db, session_id: str, fields: dict) -> dict | None:
    db.practice_sessions.update_one(
        {"session_id": session_id},
        {"$set": {**fields, "updated_at": _now(), "schema_version": SCHEMA_VERSION}},
    )
    return get_session(db, session_id)


# ---- utterances ------------------------------------------------------------


def add_utterance(db, doc: dict) -> dict:
    return _upsert(db.session_utterances, "utterance_id", doc)


def list_utterances(db, session_id: str) -> list[dict]:
    return list(
        db.session_utterances.find({"session_id": session_id}, {"_id": 0}).sort("line_index", 1)
    )


# ---- feedback + corrections ------------------------------------------------


def save_feedback(db, doc: dict) -> dict:
    return _upsert(db.coaching_feedback, "feedback_id", doc)


def get_feedback(db, session_id: str) -> dict | None:
    return db.coaching_feedback.find_one({"session_id": session_id}, {"_id": 0})


def save_correction(db, doc: dict) -> dict:
    return _upsert(db.audio_corrections, "correction_id", doc)


def list_corrections(db, session_id: str) -> list[dict]:
    return list(
        db.audio_corrections.find({"session_id": session_id}, {"_id": 0}).sort("line_index", 1)
    )


# ---- progress snapshots ----------------------------------------------------


def save_progress_snapshot(db, doc: dict) -> dict:
    return _upsert(db.progress_snapshots, "snapshot_id", doc)

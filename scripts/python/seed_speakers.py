#!/usr/bin/env python3
"""
Vaani — Speaker Seeder
Upserts all documents from seed/speakers_100.json into the speakers collection.
Safe to re-run: uses upsert keyed on slug.

Usage:
    python3 scripts/python/seed_speakers.py
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError

# ── Setup ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parents[2]
load_dotenv(ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("seed_speakers")

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://vaani_admin:vaani_secret@localhost:27017/public_speaking_intelligence?authSource=admin",
)
DB_NAME = os.getenv("MONGO_DB", "public_speaking_intelligence")

SCHEMA_VERSION = "1.0"
NOW = datetime.now(timezone.utc)

SEED_PATH = ROOT / "seed" / "speakers_100.json"


def load_speakers(path: Path) -> list:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def upsert_speakers(db, records: list) -> tuple[int, int]:
    ops = []
    for rec in records:
        doc = {**rec, "updated_at": NOW, "schema_version": SCHEMA_VERSION}
        ops.append(
            UpdateOne(
                {"slug": rec["slug"]},
                {
                    "$set": doc,
                    "$setOnInsert": {"created_at": NOW},
                },
                upsert=True,
            )
        )
    if not ops:
        return 0, 0
    try:
        result = db.speakers.bulk_write(ops, ordered=False)
        return result.upserted_count, result.modified_count
    except BulkWriteError as e:
        log.error("BulkWriteError: %s", e.details)
        raise


def validate_record(rec: dict, idx: int) -> list[str]:
    """Return list of validation errors for a speaker record."""
    errors = []
    required = [
        "canonical_name", "slug", "era", "living_status",
        "country_or_region", "profession", "profession_category",
        "overall_speaker_score", "greatness_score", "ethical_alignment_score",
        "speaking_capabilities", "schema_version",
    ]
    for field in required:
        if field not in rec:
            errors.append(f"[{idx}] missing required field: {field}")

    slug = rec.get("slug", "")
    if slug and not slug.replace("-", "").isalnum():
        errors.append(f"[{idx}] invalid slug: {slug!r}")

    for score_field in ["overall_speaker_score", "greatness_score",
                        "ethical_alignment_score", "evidence_strength_score",
                        "data_completeness_score"]:
        val = rec.get(score_field)
        if val is not None and not (0.0 <= val <= 1.0):
            errors.append(f"[{idx}] {score_field}={val} out of range [0, 1]")

    caps = rec.get("speaking_capabilities", [])
    for cap in caps:
        if "capability_id" not in cap:
            errors.append(f"[{idx}] capability missing capability_id")
        s = cap.get("strength_score")
        if s is not None and not (0.0 <= s <= 1.0):
            errors.append(f"[{idx}] capability strength_score={s} out of range")

    return errors


def main():
    log.info("Loading speakers from %s", SEED_PATH)
    speakers = load_speakers(SEED_PATH)
    log.info("  %d speakers found in seed file", len(speakers))

    # Validate
    all_errors = []
    slugs_seen = set()
    for i, rec in enumerate(speakers):
        errs = validate_record(rec, i + 1)
        all_errors.extend(errs)
        slug = rec.get("slug", "")
        if slug in slugs_seen:
            all_errors.append(f"[{i + 1}] duplicate slug: {slug!r}")
        slugs_seen.add(slug)

    if all_errors:
        log.error("Validation failed with %d error(s):", len(all_errors))
        for err in all_errors:
            log.error("  %s", err)
        sys.exit(1)
    log.info("  ✓ All %d records passed validation", len(speakers))

    log.info("Connecting to MongoDB…")
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
    except Exception as e:
        log.error("Cannot connect to MongoDB: %s", e)
        log.error("Is docker-compose up? Run: docker-compose up -d")
        sys.exit(1)

    db = client[DB_NAME]

    ins, upd = upsert_speakers(db, speakers)
    log.info("  ✓ speakers: %d inserted, %d updated", ins, upd)

    total = db.speakers.count_documents({})
    log.info("  Total in DB: %d", total)

    # ── Summary ──────────────────────────────────────────────────────────────
    log.info("")
    log.info("═══════════════════════════════════════════════")
    log.info("  Speaker seeding complete")
    log.info("  speakers collection: %d documents", total)
    log.info("═══════════════════════════════════════════════")

    client.close()


if __name__ == "__main__":
    main()

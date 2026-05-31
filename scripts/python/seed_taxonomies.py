#!/usr/bin/env python3
"""
Vaani — Taxonomy Seeder
Inserts capability_taxonomy and profession_taxonomy seed data.
Safe to re-run: uses upsert on the natural key (capability_id / profession_id).

Usage:
    python3 scripts/python/seed_taxonomies.py
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
log = logging.getLogger("seed_taxonomies")

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://vaani_admin:vaani_secret@localhost:27017/public_speaking_intelligence?authSource=admin",
)
DB_NAME = os.getenv("MONGO_DB", "public_speaking_intelligence")

SCHEMA_VERSION = "1.0"
NOW = datetime.now(timezone.utc)


def load_json(path: Path) -> list:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def upsert_capabilities(db, records: list) -> tuple[int, int]:
    ops = []
    for rec in records:
        doc = {**rec, "updated_at": NOW, "schema_version": SCHEMA_VERSION}
        ops.append(
            UpdateOne(
                {"capability_id": rec["capability_id"]},
                {"$set": doc, "$setOnInsert": {"created_at": NOW}},
                upsert=True,
            )
        )
    if not ops:
        return 0, 0
    try:
        result = db.capability_taxonomy.bulk_write(ops, ordered=False)
        return result.upserted_count, result.modified_count
    except BulkWriteError as e:
        log.error("BulkWriteError: %s", e.details)
        raise


def upsert_professions(db, records: list) -> tuple[int, int]:
    ops = []
    for rec in records:
        doc = {**rec, "updated_at": NOW, "schema_version": SCHEMA_VERSION}
        ops.append(
            UpdateOne(
                {"profession_id": rec["profession_id"]},
                {"$set": doc, "$setOnInsert": {"created_at": NOW}},
                upsert=True,
            )
        )
    if not ops:
        return 0, 0
    try:
        result = db.profession_taxonomy.bulk_write(ops, ordered=False)
        return result.upserted_count, result.modified_count
    except BulkWriteError as e:
        log.error("BulkWriteError: %s", e.details)
        raise


def main():
    log.info("Connecting to MongoDB…")
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
    except Exception as e:
        log.error("Cannot connect to MongoDB: %s", e)
        log.error("Is docker-compose up? Run: docker-compose up -d")
        sys.exit(1)

    db = client[DB_NAME]

    # ── Capability Taxonomy ──────────────────────────────────────────────────
    cap_path = ROOT / "seed" / "capability_taxonomy.json"
    log.info("Loading capabilities from %s", cap_path)
    capabilities = load_json(cap_path)
    log.info("  %d capabilities found in seed file", len(capabilities))

    ins, upd = upsert_capabilities(db, capabilities)
    log.info("  ✓ capabilities: %d inserted, %d updated", ins, upd)

    # Verify
    total_caps = db.capability_taxonomy.count_documents({})
    log.info("  Total in DB: %d", total_caps)

    # ── Profession Taxonomy ──────────────────────────────────────────────────
    prof_path = ROOT / "seed" / "profession_taxonomy.json"
    log.info("Loading professions from %s", prof_path)
    professions = load_json(prof_path)
    log.info("  %d professions found in seed file", len(professions))

    ins2, upd2 = upsert_professions(db, professions)
    log.info("  ✓ professions: %d inserted, %d updated", ins2, upd2)

    total_profs = db.profession_taxonomy.count_documents({})
    log.info("  Total in DB: %d", total_profs)

    # ── Summary ──────────────────────────────────────────────────────────────
    log.info("")
    log.info("═══════════════════════════════════════════════")
    log.info("  Taxonomy seeding complete")
    log.info("  capability_taxonomy: %d documents", total_caps)
    log.info("  profession_taxonomy: %d documents", total_profs)
    log.info("═══════════════════════════════════════════════")

    client.close()


if __name__ == "__main__":
    main()

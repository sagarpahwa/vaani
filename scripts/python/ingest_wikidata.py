#!/usr/bin/env python3
"""
Vaani — Wikidata Candidate Discovery
Discovers notable public speakers via Wikidata SPARQL and upserts them into
the candidate_speakers collection for later review and promotion.

Safe to re-run: upserts keyed on external_ids.wikidata.

Usage:
    python3 scripts/python/ingest_wikidata.py [--dry-run] [--max-records N]
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError
from tqdm import tqdm

ROOT = Path(__file__).parents[2]
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT))

from scripts.python.utils.wikidata import fetch_page, parse_row, OCCUPATION_MAP, PAGE_SIZE
from scripts.python.utils.slugify_utils import make_slug

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ingest_wikidata")

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://vaani_admin:vaani_secret@localhost:27017/public_speaking_intelligence?authSource=admin",
)
DB_NAME = os.getenv("MONGO_DB", "public_speaking_intelligence")
SCHEMA_VERSION = "1.0"
UPSERT_BATCH = 100  # docs per bulk_write call


def get_existing_wikidata_ids(db) -> set[str]:
    """Return wikidata_ids already present in the verified speakers collection."""
    cursor = db.speakers.find(
        {"external_ids.wikidata": {"$exists": True, "$ne": ""}},
        {"external_ids.wikidata": 1},
    )
    return {
        doc["external_ids"]["wikidata"]
        for doc in cursor
        if doc.get("external_ids", {}).get("wikidata")
    }


def build_doc(parsed: dict, now: datetime) -> dict:
    return {
        "canonical_name": parsed["canonical_name"],
        "slug": make_slug(parsed["canonical_name"]),
        "source": "wikidata",
        "external_ids": {
            "wikidata": parsed["wikidata_id"],
            "wikipedia": parsed["wikipedia_title"],
        },
        "profession_category": parsed["profession_category"],
        "country_or_region": parsed["country_or_region"],
        "birth_year": parsed["birth_year"],
        "death_year": parsed["death_year"],
        "verification_status": "pending",
        "raw_data": {
            "wikidata_id": parsed["wikidata_id"],
            "occupation_qid": parsed["occupation_qid"],
            "wikipedia_title": parsed["wikipedia_title"],
        },
        "updated_at": now,
        "schema_version": SCHEMA_VERSION,
    }


def upsert_batch(db, docs: list[dict], now: datetime) -> tuple[int, int]:
    ops = [
        UpdateOne(
            {"external_ids.wikidata": d["external_ids"]["wikidata"]},
            {"$set": d, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        for d in docs
    ]
    try:
        r = db.candidate_speakers.bulk_write(ops, ordered=False)
        return r.upserted_count, r.modified_count
    except BulkWriteError as e:
        log.error("BulkWriteError: %d errors", len(e.details.get("writeErrors", [])))
        raise


def main():
    parser = argparse.ArgumentParser(description="Ingest Wikidata candidate speakers")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and parse but skip DB writes")
    parser.add_argument("--max-records", type=int, default=10_000, help="Max new candidates to process")
    args = parser.parse_args()

    log.info("Connecting to MongoDB…")
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
    except Exception as e:
        log.error("Cannot connect to MongoDB: %s", e)
        sys.exit(1)

    db = client[DB_NAME]
    now = datetime.now(timezone.utc)

    if args.dry_run:
        log.info("DRY RUN — no data will be written to the database")

    existing_ids = get_existing_wikidata_ids(db)
    log.info("Skipping %d wikidata_ids already in speakers collection", len(existing_ids))

    # Start extraction_run log entry
    run_id = None
    if not args.dry_run:
        run_id = db.extraction_runs.insert_one({
            "run_type": "wikidata_candidates",
            "started_at": now,
            "status": "running",
            "sources_used": ["https://query.wikidata.org/sparql"],
            "query": f"{len(OCCUPATION_MAP)} occupation QIDs, English Wikipedia required",
            "records_found": None,
            "records_inserted": None,
            "records_updated": None,
            "records_skipped": None,
            "errors": [],
        }).inserted_id

    total_found = total_inserted = total_updated = total_skipped = 0
    seen: set[str] = set()
    pending: list[dict] = []
    errors: list[dict] = []

    pbar = tqdm(desc="Candidates discovered", unit="rec")
    done = False
    try:
        for occ_qid, prof_cat in OCCUPATION_MAP.items():
            if done:
                break
            log.info("Querying occupation %s (%s)…", occ_qid, prof_cat)
            offset = 0
            while True:
                try:
                    rows = fetch_page(occ_qid, offset)
                except Exception as e:
                    errors.append({"error_type": "sparql_error", "message": str(e)[:200], "count": 1})
                    log.warning("Skipping occupation %s after error: %s", occ_qid, e)
                    break

                if not rows:
                    break

                for row in rows:
                    parsed = parse_row(row, occ_qid)
                    if not parsed:
                        continue

                    qid = parsed["wikidata_id"]
                    if qid in existing_ids or qid in seen:
                        total_skipped += 1
                        continue

                    seen.add(qid)
                    total_found += 1
                    pbar.update(1)

                    if not args.dry_run:
                        pending.append(build_doc(parsed, now))

                    if len(pending) >= UPSERT_BATCH:
                        ins, upd = upsert_batch(db, pending, now)
                        total_inserted += ins
                        total_updated += upd
                        pending.clear()

                    if total_found >= args.max_records:
                        log.info("Reached --max-records limit (%d)", args.max_records)
                        done = True
                        break

                if done or len(rows) < PAGE_SIZE:
                    break
                offset += PAGE_SIZE

        # Flush remainder
        if pending:
            ins, upd = upsert_batch(db, pending, now)
            total_inserted += ins
            total_updated += upd

    finally:
        pbar.close()

    completed_at = datetime.now(timezone.utc)
    status = "completed" if not errors else "partial"

    log.info("")
    log.info("═══════════════════════════════════════════")
    log.info("  Wikidata candidate ingestion complete")
    log.info("  New candidates found:  %d", total_found)
    log.info("  Skipped (seen/exists): %d", total_skipped)
    if not args.dry_run:
        log.info("  Inserted:              %d", total_inserted)
        log.info("  Updated:               %d", total_updated)
        total_in_db = db.candidate_speakers.count_documents({})
        log.info("  Total in DB now:       %d", total_in_db)
    log.info("  Status:                %s", status)
    log.info("═══════════════════════════════════════════")

    if run_id:
        db.extraction_runs.update_one(
            {"_id": run_id},
            {"$set": {
                "completed_at": completed_at,
                "status": status,
                "records_found": total_found,
                "records_inserted": total_inserted,
                "records_updated": total_updated,
                "records_skipped": total_skipped,
                "errors": errors,
            }},
        )

    client.close()


if __name__ == "__main__":
    main()

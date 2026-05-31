"""
Integration tests — require a running MongoDB instance.
Run with: pytest tests/integration/ -m integration

In CI, MongoDB is provided as a Docker service (see .github/workflows/integration.yml).
Locally: make db-up first.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "python"))

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://vaani_admin:vaani_secret@localhost:27017/public_speaking_intelligence?authSource=admin",
)
DB_NAME = os.getenv("MONGO_DB", "public_speaking_intelligence")


@pytest.fixture(scope="module")
def mongo_client():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    yield client
    client.close()


@pytest.fixture(scope="module")
def db(mongo_client):
    return mongo_client[DB_NAME]


@pytest.mark.integration
def test_db_connection_succeeds(mongo_client):
    result = mongo_client.admin.command("ping")
    assert result.get("ok") == 1.0


@pytest.mark.integration
def test_seed_speakers_round_trip(db):
    from seed_speakers import load_speakers, upsert_speakers

    speakers = load_speakers(ROOT / "seed" / "speakers_100.json")
    upsert_speakers(db, speakers)
    count = db.speakers.count_documents({})
    assert count >= 100, f"Expected >=100 speakers in DB, got {count}"


@pytest.mark.integration
def test_seed_speakers_idempotent(db):
    from seed_speakers import load_speakers, upsert_speakers

    speakers = load_speakers(ROOT / "seed" / "speakers_100.json")
    count_before = db.speakers.count_documents({})
    upsert_speakers(db, speakers)
    count_after = db.speakers.count_documents({})
    assert count_before == count_after, "Re-seeding changed the document count"


@pytest.mark.integration
def test_seed_taxonomies_round_trip(db):
    from seed_taxonomies import load_json, upsert_capabilities, upsert_professions

    caps = load_json(ROOT / "seed" / "capability_taxonomy.json")
    profs = load_json(ROOT / "seed" / "profession_taxonomy.json")
    upsert_capabilities(db, caps)
    upsert_professions(db, profs)
    assert db.capability_taxonomy.count_documents({}) >= 25
    assert db.profession_taxonomy.count_documents({}) >= 20


@pytest.mark.integration
def test_slug_unique_index_enforced(db):
    slug = "__integration_test_unique_slug__"
    db.speakers.delete_many({"slug": slug})
    db.speakers.insert_one({"slug": slug, "canonical_name": "A"})
    with pytest.raises(DuplicateKeyError):
        db.speakers.insert_one({"slug": slug, "canonical_name": "B"})
    db.speakers.delete_many({"slug": slug})


@pytest.mark.integration
def test_verify_script_exits_zero():
    result = subprocess.run(
        ["node", "scripts/node/verify.js"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        env={**os.environ, "MONGO_URI": MONGO_URI, "MONGO_DB": DB_NAME},
    )
    assert result.returncode == 0, (
        f"verify.js exited {result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )

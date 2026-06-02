"""Tests for mock-DB seeding: idempotent upserts, audit fields, seed integrity."""

from services.api.db.init_mock_db import init_db
from services.api.db.seed_mock import SEED_DIR, load_json, seed_all, upsert_docs


def test_upsert_docs_empty_returns_zero(db):
    assert upsert_docs(db.users, [], "user_id") == (0, 0)


def test_upsert_docs_inserts_then_updates(db):
    recs = [{"user_id": "u1", "display_name": "One"}]
    ins, upd = upsert_docs(db.users, recs, "user_id")
    assert (ins, upd) == (1, 0)
    # Second run updates, does not duplicate.
    ins2, upd2 = upsert_docs(db.users, recs, "user_id")
    assert ins2 == 0
    assert db.users.count_documents({}) == 1


def test_upsert_sets_audit_fields(db):
    upsert_docs(db.users, [{"user_id": "u1", "display_name": "One"}], "user_id")
    doc = db.users.find_one({"user_id": "u1"})
    assert doc["schema_version"] == "1.0"
    assert "created_at" in doc and "updated_at" in doc


def test_seed_all_loads_real_seed_files(db):
    init_db(db, apply_validators=False)
    summary = seed_all(db)
    assert summary["guided_scripts"][0] == 4  # 4 scripts inserted
    assert summary["users"][0] == 1
    assert summary["learner_profiles"][0] == 1
    assert db.guided_scripts.count_documents({}) == 4


def test_seed_all_is_idempotent(db):
    init_db(db, apply_validators=False)
    seed_all(db)
    second = seed_all(db)
    # No new inserts on re-run.
    assert all(ins == 0 for ins, _ in second.values())
    assert db.guided_scripts.count_documents({}) == 4


def test_seed_guided_scripts_have_required_fields():
    scripts = load_json(SEED_DIR / "guided_scripts.json")
    assert len(scripts) >= 4
    ids = [s["script_id"] for s in scripts]
    assert len(ids) == len(set(ids)), "duplicate script_id in seed"
    for s in scripts:
        assert s["title"] and s["lines"]
        for line in s["lines"]:
            assert "line_index" in line and line["text"]

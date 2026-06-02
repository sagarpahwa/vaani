"""Tests for mock-DB initialization + the hard-isolation safety guard."""

import pytest

from services.api.db.init_mock_db import (
    COLLECTION_SPECS,
    assert_mock_target,
    init_db,
    load_schema,
)

ALL_COLLECTIONS = {spec["name"] for spec in COLLECTION_SPECS}


def test_init_creates_all_collections(db):
    summary = init_db(db, apply_validators=False)
    assert set(summary["created"]) == ALL_COLLECTIONS
    assert set(db.list_collection_names()) >= ALL_COLLECTIONS
    assert summary["indexes"] > 0


def test_init_is_idempotent(db):
    init_db(db, apply_validators=False)
    second = init_db(db, apply_validators=False)
    assert second["created"] == []
    assert set(second["existing"]) == ALL_COLLECTIONS


def test_init_creates_unique_key_indexes(db):
    init_db(db, apply_validators=False)
    idx = db.guided_scripts.index_information()
    unique_keys = [v["key"][0][0] for v in idx.values() if v.get("unique")]
    assert "script_id" in unique_keys


def test_apply_validators_does_not_crash_on_mock(db):
    # mongomock cannot enforce collMod validators; init must still succeed.
    summary = init_db(db, apply_validators=True)
    assert set(summary["created"]) == ALL_COLLECTIONS


def test_load_schema_returns_json_schema():
    schema = load_schema("practice_sessions")
    assert "$jsonSchema" in schema


def test_assert_mock_target_accepts_mock_db():
    # Should not raise.
    assert_mock_target("mongodb://localhost:27018", "public_speaking_intelligence_mock")


def test_assert_mock_target_rejects_non_mock_db():
    with pytest.raises(RuntimeError, match="not a '\\*_mock'"):
        assert_mock_target("mongodb://localhost:27018", "public_speaking_intelligence")


def test_assert_mock_target_rejects_real_port():
    with pytest.raises(RuntimeError, match="27017"):
        assert_mock_target("mongodb://localhost:27017", "public_speaking_intelligence_mock")

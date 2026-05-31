"""Unit tests for persistence helpers: audit fields, ordering, round-trips."""

from services.api import repository as repo


def test_create_and_get_session_sets_audit_fields(db):
    repo.create_session(
        db, {"session_id": "s1", "user_id": "u", "mode": "guided", "status": "created"}
    )
    s = repo.get_session(db, "s1")
    assert s["schema_version"] == "1.0"
    assert "created_at" in s and "updated_at" in s


def test_update_session_changes_status(db):
    repo.create_session(
        db, {"session_id": "s1", "user_id": "u", "mode": "guided", "status": "created"}
    )
    repo.update_session(db, "s1", {"status": "scored", "overall_score": 0.8})
    s = repo.get_session(db, "s1")
    assert s["status"] == "scored"
    assert s["overall_score"] == 0.8


def test_get_missing_session_is_none(db):
    assert repo.get_session(db, "nope") is None


def test_utterances_listed_in_line_order(db):
    repo.add_utterance(db, {"utterance_id": "s1:1", "session_id": "s1", "line_index": 1})
    repo.add_utterance(db, {"utterance_id": "s1:0", "session_id": "s1", "line_index": 0})
    items = repo.list_utterances(db, "s1")
    assert [i["line_index"] for i in items] == [0, 1]


def test_feedback_and_corrections_round_trip(db):
    repo.save_feedback(db, {"feedback_id": "s1:f", "session_id": "s1", "summary": "good"})
    assert repo.get_feedback(db, "s1")["summary"] == "good"
    repo.save_correction(db, {"correction_id": "s1:0", "session_id": "s1", "line_index": 0})
    assert len(repo.list_corrections(db, "s1")) == 1


def test_progress_snapshot_saved(db):
    repo.save_progress_snapshot(db, {"snapshot_id": "s1:snap", "user_id": "u", "session_id": "s1"})
    assert db.progress_snapshots.count_documents({}) == 1


def test_list_scripts_empty_db(db):
    assert repo.list_scripts(db) == []

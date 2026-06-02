"""Integration test: full Mode A + Mode B flows against the real mock MongoDB.

Requires the isolated POC Mongo (port 27018). Skips cleanly when it isn't up,
so `make poc-api-test-all` never hard-fails on a developer box without Docker.
Targets ONLY the `*_mock` DB (guarded) and deletes the docs it creates.

Run: `make poc-db-up && make poc-db-setup && make poc-api-test-all`.
"""

import base64

import pytest

from services.api.config import Settings
from services.api.db.init_mock_db import assert_mock_target, init_db
from services.api.db.seed_mock import seed_all
from services.api.providers.object_store import LocalFSObjectStore
from services.api.providers.registry import build_providers

pytestmark = pytest.mark.integration

B64_AUDIO = base64.b64encode(b"fake-recording-bytes").decode()


@pytest.fixture
def real_client(tmp_path):
    from fastapi.testclient import TestClient
    from pymongo import MongoClient

    from services.api.app import create_app

    settings = Settings()
    assert_mock_target(settings.poc_mongo_uri, settings.poc_mongo_db)
    mongo = MongoClient(settings.poc_mongo_uri, serverSelectionTimeoutMS=2000)
    try:
        mongo.admin.command("ping")
    except Exception:
        pytest.skip("mock MongoDB not reachable on :27018 (run `make poc-db-up`)")

    db = mongo[settings.poc_mongo_db]
    init_db(db, apply_validators=True)
    seed_all(db)
    providers = build_providers(settings, store=LocalFSObjectStore(tmp_path))
    app = create_app(settings=settings, db=db, providers=providers)

    created_session_ids: list[str] = []
    yield TestClient(app), created_session_ids

    # Clean up only the docs this test created.
    for sid in created_session_ids:
        for coll in (
            "practice_sessions",
            "session_utterances",
            "coaching_feedback",
            "audio_corrections",
            "progress_snapshots",
        ):
            db[coll].delete_many({"session_id": sid})
        db.practice_sessions.delete_many({"parent_session_id": sid})
    mongo.close()


def test_mode_a_full_flow_persists_to_real_mock_db(real_client):
    client, created = real_client
    session = client.post(
        "/sessions",
        json={"user_id": "demo-user", "mode": "guided", "script_id": "self-intro-60s"},
    ).json()
    created.append(session["session_id"])

    utts = [
        {"line_index": i, "audio_base64": B64_AUDIO} for i in range(len(session["expected_units"]))
    ]
    scored = client.post(
        f"/sessions/{session['session_id']}/utterances", json={"utterances": utts}
    ).json()
    assert scored["status"] == "scored"
    assert scored["versions"]["rubric_version"]

    # Persisted and re-fetchable from the real DB.
    fetched = client.get(f"/sessions/{session['session_id']}").json()
    assert fetched["status"] == "scored"
    assert fetched["feedback"]["summary"]


def test_mode_b_full_flow_against_real_mock_db(real_client):
    client, created = real_client
    session = client.post(
        "/sessions",
        json={
            "user_id": "demo-user",
            "mode": "user_script",
            "script_text": "Friends, today we begin.\nTomorrow we go further.",
        },
    ).json()
    created.append(session["session_id"])
    assert len(session["expected_units"]) == 2

    utts = [{"line_index": i, "audio_base64": B64_AUDIO} for i in range(2)]
    scored = client.post(
        f"/sessions/{session['session_id']}/utterances", json={"utterances": utts}
    ).json()
    assert scored["status"] == "scored"
    assert 0.0 <= scored["overall_score"] <= 1.0

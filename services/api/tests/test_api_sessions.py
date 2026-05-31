"""Contract tests for the full session lifecycle: create, score, get, retry.

Covers both Mode A (guided script) and Mode B (user-provided script), plus the
error paths. Assertions are structural (status, score bounds, presence of
feedback/versions/delta) since the mock pipeline is deterministic but its exact
numbers are an implementation detail.
"""

import base64

B64_AUDIO = base64.b64encode(b"fake-recording-bytes").decode()


def _create_guided(client, script_id="self-intro-60s"):
    r = client.post(
        "/sessions",
        json={
            "user_id": "demo-user",
            "mode": "guided",
            "script_id": script_id,
            "goal_signature": {"occasion": "self introduction"},
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _submit_all_lines(client, session):
    utts = [
        {"line_index": i, "audio_base64": B64_AUDIO} for i in range(len(session["expected_units"]))
    ]
    return client.post(f"/sessions/{session['session_id']}/utterances", json={"utterances": utts})


def test_create_guided_session(client):
    body = _create_guided(client)
    assert body["mode"] == "guided"
    assert body["status"] == "created"
    assert body["attempt"] == 1
    assert len(body["expected_units"]) >= 1


def test_guided_full_flow_scores(client):
    session = _create_guided(client)
    r = _submit_all_lines(client, session)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "scored"
    assert 0.0 <= body["overall_score"] <= 1.0
    assert set(body["capability_scores"])
    assert body["feedback"]["summary"]
    assert body["feedback"]["read_aloud_text"]
    assert body["versions"]["rubric_version"]
    assert body["versions"]["scoring_model_version"]
    for c in body["corrections"]:
        assert c["ideal_audio_key"]


def test_get_session_after_scoring(client):
    session = _create_guided(client)
    _submit_all_lines(client, session)
    r = client.get(f"/sessions/{session['session_id']}")
    assert r.status_code == 200
    assert r.json()["session_id"] == session["session_id"]
    assert r.json()["status"] == "scored"


def test_user_script_mode_flow(client):
    r = client.post(
        "/sessions",
        json={
            "user_id": "demo-user",
            "mode": "user_script",
            "script_text": "We will win this together.\nWe will not yield.",
            "goal_signature": {"objective": "rally the team"},
        },
    )
    assert r.status_code == 201, r.text
    session = r.json()
    assert session["mode"] == "user_script"
    assert len(session["expected_units"]) == 2
    scored = _submit_all_lines(client, session).json()
    assert scored["status"] == "scored"
    assert scored["feedback"] is not None


def test_retry_reports_delta_and_increments_attempt(client):
    session = _create_guided(client)
    n = len(session["expected_units"])
    _submit_all_lines(client, session)
    retry = client.post(
        f"/sessions/{session['session_id']}/retry",
        json={"utterances": [{"line_index": i, "audio_base64": B64_AUDIO} for i in range(n)]},
    )
    assert retry.status_code == 201, retry.text
    body = retry.json()
    assert body["attempt"] == 2
    assert body["parent_session_id"] == session["session_id"]
    assert body["status"] == "scored"
    assert body["delta"] is not None
    assert "overall" in body["delta"]


# ---- error paths -----------------------------------------------------------


def test_create_guided_unknown_script_404(client):
    r = client.post("/sessions", json={"user_id": "u", "mode": "guided", "script_id": "nope"})
    assert r.status_code == 404


def test_create_user_script_blank_422(client):
    r = client.post("/sessions", json={"user_id": "u", "mode": "user_script", "script_text": "   "})
    assert r.status_code == 422


def test_submit_to_unknown_session_404(client):
    r = client.post("/sessions/nope/utterances", json={"utterances": [{"line_index": 0}]})
    assert r.status_code == 404


def test_submit_empty_utterances_422(client):
    session = _create_guided(client)
    r = client.post(f"/sessions/{session['session_id']}/utterances", json={"utterances": []})
    assert r.status_code == 422


def test_get_unknown_session_404(client):
    assert client.get("/sessions/nope").status_code == 404


def test_retry_unknown_session_404(client):
    r = client.post("/sessions/nope/retry", json={"utterances": [{"line_index": 0}]})
    assert r.status_code == 404

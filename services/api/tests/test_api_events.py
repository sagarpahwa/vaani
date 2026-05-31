"""Contract tests for the WebSocket progress stream."""

import base64

B64_AUDIO = base64.b64encode(b"fake-recording-bytes").decode()


def _scored_session(client):
    session = client.post(
        "/sessions",
        json={"user_id": "demo-user", "mode": "guided", "script_id": "self-intro-60s"},
    ).json()
    utts = [
        {"line_index": i, "audio_base64": B64_AUDIO} for i in range(len(session["expected_units"]))
    ]
    client.post(f"/sessions/{session['session_id']}/utterances", json={"utterances": utts})
    return session["session_id"]


def test_ws_streams_stages_then_done(client):
    session_id = _scored_session(client)
    stages = []
    with client.websocket_connect(f"/sessions/{session_id}/events") as ws:
        while True:
            msg = ws.receive_json()
            stages.append(msg["stage"])
            if msg["stage"] == "done":
                assert msg["status"] == "scored"
                assert 0.0 <= msg["overall_score"] <= 1.0
                break
    assert "transcribing" in stages
    assert "scoring" in stages
    assert stages[-1] == "done"


def test_ws_unknown_session_emits_error(client):
    with client.websocket_connect("/sessions/nope/events") as ws:
        msg = ws.receive_json()
        assert msg["stage"] == "error"

"""Contract tests for the persona endpoints (20 Legends)."""


def test_list_personas_returns_seeded_twenty(client):
    r = client.get("/personas")
    assert r.status_code == 200
    personas = r.json()
    assert len(personas) == 20
    assert all(p["line_count"] >= 1 for p in personas)
    assert all(p["persona_id"] and p["name"] for p in personas)


def test_get_persona_detail(client):
    r = client.get("/personas/steve-jobs")
    assert r.status_code == 200
    body = r.json()
    assert body["persona_id"] == "steve-jobs"
    assert body["name"] == "Steve Jobs"
    assert body["lines"] and "text" in body["lines"][0]
    assert body["goal_line"]
    assert body["signature_qualities"]


def test_persona_detail_exposes_pace_band_not_weights(client):
    body = client.get("/personas/warren-buffett").json()
    band = body["rubric"]["target_pace_sps"]
    assert band == [2.4, 3.0]
    assert body["rubric"]["pause_style"] in {"steady", "dramatic", "brisk"}
    # internal scoring weights/feedback notes must not leak to the wire
    assert "capability_weights" not in body["rubric"]
    assert "feedback_notes" not in body["rubric"]


def test_persona_reference_url_may_be_null(client):
    # Elon Musk had no verified URL provided, so it is null (never fabricated).
    body = client.get("/personas/elon-musk").json()
    assert body["reference"]["video_url"] is None
    # Steve Jobs has the user-provided Stanford link.
    jobs = client.get("/personas/steve-jobs").json()
    assert jobs["reference"]["video_url"].startswith("https://www.youtube.com/")


def test_get_unknown_persona_404(client):
    assert client.get("/personas/does-not-exist").status_code == 404

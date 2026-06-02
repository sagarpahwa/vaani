"""Contract tests for the guided-script endpoints (Mode A)."""


def test_list_scripts_returns_seeded_four(client):
    r = client.get("/scripts")
    assert r.status_code == 200
    scripts = r.json()
    assert len(scripts) == 4
    assert all("line_count" in s and s["line_count"] >= 1 for s in scripts)


def test_get_script_detail(client):
    r = client.get("/scripts/self-intro-60s")
    assert r.status_code == 200
    body = r.json()
    assert body["script_id"] == "self-intro-60s"
    assert body["lines"]
    assert "text" in body["lines"][0]


def test_get_unknown_script_404(client):
    assert client.get("/scripts/does-not-exist").status_code == 404

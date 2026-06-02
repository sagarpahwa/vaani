from fastapi.testclient import TestClient

from services.api.app import create_app

client = TestClient(create_app())


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == "vaani-coaching-api"


def test_root_ok():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["docs"] == "/docs"

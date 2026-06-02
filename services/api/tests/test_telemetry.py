"""Unit tests for release-health telemetry emission."""

from services.api import repository as repo
from services.api import telemetry as tel
from services.api.telemetry import Telemetry


def test_emit_builds_schema_shaped_event_without_db():
    event = Telemetry(None).emit("custom", session_id="s1", latency_ms=12.7, foo="bar")
    assert event["event_id"]
    assert event["event_type"] == "custom"
    assert event["session_id"] == "s1"
    assert event["severity"] == "info"
    assert event["latency_ms"] == 13  # coerced to non-negative int
    assert event["success"] is None
    assert event["payload"] == {"foo": "bar"}


def test_emit_persists_when_db_given(db):
    Telemetry(db).scoring("s2", success=True, latency_ms=8.2, overall_score=0.9)
    stored = db.release_health_events.find_one({"session_id": "s2"}, {"_id": 0})
    assert stored is not None
    assert stored["event_type"] == tel.SCORING
    assert stored["success"] is True
    assert stored["latency_ms"] == 8
    assert stored["created_at"] and stored["updated_at"]
    assert stored["schema_version"] == repo.SCHEMA_VERSION


def test_emit_is_best_effort_and_never_raises():
    class _BoomCollection:
        def update_one(self, *a, **k):
            raise RuntimeError("db down")

    class _BoomDB:
        release_health_events = _BoomCollection()

    # Must not propagate the DB error to the caller (request path stays alive).
    event = Telemetry(_BoomDB()).emit("scoring", success=False)
    assert event["event_type"] == "scoring"


def test_unknown_severity_falls_back_to_info():
    assert Telemetry(None).emit("x", severity="catastrophic")["severity"] == "info"


def test_negative_latency_is_clamped_to_zero():
    assert Telemetry(None).emit("x", latency_ms=-5)["latency_ms"] == 0


def test_named_emitters_set_severity_and_success():
    t = Telemetry(None)
    assert t.scoring("s", success=False)["severity"] == "error"
    assert t.transcription("s", success=False)["severity"] == "error"
    completed = t.session_completed("s", status="failed")
    assert completed["severity"] == "warn"
    assert completed["success"] is False
    ok = t.session_completed("s", status="scored", overall_score=0.8)
    assert ok["severity"] == "info"
    assert ok["success"] is True
    assert t.ab_playback("s", success=False)["severity"] == "warn"
    err = t.api_error(endpoint="/sessions", error_class="HTTPException", status=404)
    assert err["severity"] == "error"
    assert err["payload"]["status"] == 404
    crash = t.mobile_crash(platform="android", detail="ANR")
    assert crash["event_type"] == tel.MOBILE_CRASH
    assert t.retry_delta("s", overall_delta=0.05)["payload"]["overall_delta"] == 0.05
    assert t.feedback_latency("s", latency_ms=100)["event_type"] == tel.FEEDBACK_LATENCY
    assert t.session_started("s", mode="guided")["payload"]["mode"] == "guided"

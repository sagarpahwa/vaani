"""Release-health telemetry emission (POC).

Events persist to the `release_health_events` collection so the SLOs in
`docs/reliability/slos.md` can be measured from real traffic. Plan §11.1
enumerates the event types; the named emitters below cover each.

Emission is **best-effort**: a telemetry failure (bad DB, validator rejection)
must never break a coaching request, so persistence is wrapped and swallowed.
Pure event construction is kept separate from the DB write, so the emitters are
unit-testable without a database.
"""

from uuid import uuid4

from . import repository as repo

# Event-type taxonomy (plan §11.1). success/failure variants fold into the
# `success` bool; per-class counts ride in `payload`.
SESSION_STARTED = "session_started"
SESSION_COMPLETED = "session_completed"
TRANSCRIPTION = "transcription"
SCORING = "scoring"
FEEDBACK_LATENCY = "feedback_latency"
AB_PLAYBACK = "ab_playback"
RETRY_DELTA = "retry_delta"
API_ERROR = "api_error"
MOBILE_CRASH = "mobile_crash"

_SEVERITIES = {"info", "warn", "error"}


class Telemetry:
    """Emits release-health events. Construct with a Mongo DB handle to persist;
    pass `None` (or omit) for a build-only, no-write instance."""

    def __init__(self, db=None):
        self.db = db

    def emit(
        self,
        event_type: str,
        *,
        session_id: str | None = None,
        severity: str = "info",
        latency_ms: float | int | None = None,
        success: bool | None = None,
        **payload,
    ) -> dict:
        """Build a schema-shaped event, persist it best-effort, and return it.

        `latency_ms` is coerced to a non-negative int (the schema's bsonType).
        Unknown severities fall back to ``info`` rather than risk a validator
        rejection on the request path.
        """
        if severity not in _SEVERITIES:
            severity = "info"
        ms = None if latency_ms is None else max(0, int(round(latency_ms)))
        event = {
            "event_id": uuid4().hex,
            "event_type": event_type,
            "session_id": session_id,
            "severity": severity,
            "latency_ms": ms,
            "success": success,
            "payload": payload,
        }
        if self.db is not None:
            try:
                repo.save_event(self.db, event)
            except Exception:
                # Telemetry is best-effort; never break the request it observes.
                pass
        return event

    # ---- named emitters (one per plan §11.1 category) ----------------------

    def session_started(self, session_id: str, *, mode: str, attempt: int = 1) -> dict:
        return self.emit(SESSION_STARTED, session_id=session_id, mode=mode, attempt=attempt)

    def session_completed(
        self,
        session_id: str,
        *,
        status: str,
        overall_score: float | None = None,
        latency_ms: float | int | None = None,
    ) -> dict:
        ok = status == "scored"
        return self.emit(
            SESSION_COMPLETED,
            session_id=session_id,
            severity="info" if ok else "warn",
            success=ok,
            latency_ms=latency_ms,
            status=status,
            overall_score=overall_score,
        )

    def transcription(self, session_id: str, *, success: bool, count: int | None = None) -> dict:
        return self.emit(
            TRANSCRIPTION,
            session_id=session_id,
            severity="info" if success else "error",
            success=success,
            count=count,
        )

    def scoring(
        self,
        session_id: str,
        *,
        success: bool,
        latency_ms: float | int | None = None,
        overall_score: float | None = None,
    ) -> dict:
        return self.emit(
            SCORING,
            session_id=session_id,
            severity="info" if success else "error",
            success=success,
            latency_ms=latency_ms,
            overall_score=overall_score,
        )

    def feedback_latency(self, session_id: str, *, latency_ms: float | int) -> dict:
        return self.emit(FEEDBACK_LATENCY, session_id=session_id, latency_ms=latency_ms)

    def ab_playback(self, session_id: str | None, *, success: bool) -> dict:
        return self.emit(
            AB_PLAYBACK,
            session_id=session_id,
            severity="info" if success else "warn",
            success=success,
        )

    def retry_delta(self, session_id: str, *, overall_delta: float) -> dict:
        return self.emit(RETRY_DELTA, session_id=session_id, overall_delta=overall_delta)

    def api_error(
        self, *, endpoint: str, error_class: str, status: int, session_id: str | None = None
    ) -> dict:
        return self.emit(
            API_ERROR,
            session_id=session_id,
            severity="error",
            success=False,
            endpoint=endpoint,
            error_class=error_class,
            status=status,
        )

    def mobile_crash(
        self, *, platform: str, detail: str | None = None, session_id: str | None = None
    ) -> dict:
        return self.emit(
            MOBILE_CRASH,
            session_id=session_id,
            severity="error",
            success=False,
            platform=platform,
            detail=detail,
        )

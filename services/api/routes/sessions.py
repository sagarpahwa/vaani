"""Practice-session endpoints: create, fetch, submit utterances, retry.

Submitting utterances runs the (synchronous, deterministic) coaching pipeline
and returns the scored session detail. Retry forks a child session and reports
the per-capability delta versus the parent attempt.
"""

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from .. import repository as repo
from ..coaching_service import (
    assemble_detail,
    process_session,
    resolve_expected_units,
    store_utterances,
)
from ..deps import get_db, get_pipeline, get_providers
from ..models import (
    CreateSessionRequest,
    RetryRequest,
    SessionDetail,
    SubmitUtterancesRequest,
)
from ..telemetry import Telemetry

router = APIRouter(tags=["sessions"])


@router.post("/sessions", response_model=SessionDetail, status_code=201)
def create_session(req: CreateSessionRequest, db=Depends(get_db)):
    expected_units, script_id = resolve_expected_units(db, req.mode, req.script_id, req.script_text)
    if expected_units is None:
        raise HTTPException(status_code=404, detail="guided script not found")
    if not expected_units:
        raise HTTPException(status_code=422, detail="no script lines to practice")

    session_id = uuid4().hex
    doc = {
        "session_id": session_id,
        "user_id": req.user_id,
        "mode": req.mode,
        "status": "created",
        "script_id": script_id,
        "expected_units": expected_units,
        "goal_signature": (req.goal_signature.model_dump() if req.goal_signature else {}),
        "attempt": 1,
    }
    if req.mode == "user_script":
        doc["user_script_text"] = req.script_text or ""
    repo.create_session(db, doc)
    Telemetry(db).session_started(session_id, mode=req.mode, attempt=1)
    return SessionDetail(**assemble_detail(db, repo.get_session(db, session_id)))


@router.get("/sessions/{session_id}", response_model=SessionDetail)
def get_session(session_id: str, db=Depends(get_db)):
    session = repo.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    return SessionDetail(**assemble_detail(db, session))


@router.post("/sessions/{session_id}/utterances", response_model=SessionDetail)
def submit_utterances(
    session_id: str,
    req: SubmitUtterancesRequest,
    db=Depends(get_db),
    providers=Depends(get_providers),
    pipeline=Depends(get_pipeline),
):
    session = repo.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    if not req.utterances:
        raise HTTPException(status_code=422, detail="no utterances submitted")

    telemetry = Telemetry(db)
    repo.update_session(db, session_id, {"status": "recording"})
    store_utterances(providers, db, session_id, req.utterances, session.get("expected_units", []))
    scored = process_session(db, pipeline, repo.get_session(db, session_id), telemetry=telemetry)
    telemetry.session_completed(
        session_id, status=scored["status"], overall_score=scored.get("overall_score")
    )
    return SessionDetail(**assemble_detail(db, repo.get_session(db, session_id)))


@router.post("/sessions/{session_id}/retry", response_model=SessionDetail, status_code=201)
def retry_session(
    session_id: str,
    req: RetryRequest,
    db=Depends(get_db),
    providers=Depends(get_providers),
    pipeline=Depends(get_pipeline),
):
    parent = repo.get_session(db, session_id)
    if not parent:
        raise HTTPException(status_code=404, detail="session not found")
    if not req.utterances:
        raise HTTPException(status_code=422, detail="no utterances submitted")

    parent_scores = {
        "overall": parent.get("overall_score") or 0.0,
        **(parent.get("capability_scores") or {}),
    }
    child_id = uuid4().hex
    child = {
        "session_id": child_id,
        "user_id": parent["user_id"],
        "mode": parent["mode"],
        "status": "recording",
        "script_id": parent.get("script_id"),
        "expected_units": parent.get("expected_units", []),
        "goal_signature": parent.get("goal_signature") or {},
        "attempt": parent.get("attempt", 1) + 1,
        "parent_session_id": session_id,
    }
    if parent.get("user_script_text"):
        child["user_script_text"] = parent["user_script_text"]
    repo.create_session(db, child)
    telemetry = Telemetry(db)
    telemetry.session_started(child_id, mode=child["mode"], attempt=child["attempt"])
    store_utterances(providers, db, child_id, req.utterances, child["expected_units"])
    scored = process_session(
        db,
        pipeline,
        repo.get_session(db, child_id),
        parent_scores=parent_scores,
        telemetry=telemetry,
    )
    telemetry.session_completed(
        child_id, status=scored["status"], overall_score=scored.get("overall_score")
    )
    delta = scored.get("delta") or {}
    if "overall" in delta:
        telemetry.retry_delta(child_id, overall_delta=delta["overall"])
    return SessionDetail(**assemble_detail(db, repo.get_session(db, child_id)))

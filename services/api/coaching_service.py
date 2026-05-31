"""Orchestration between the API routes, persistence, and the domain pipeline.

Routes stay thin: they validate input and call into here. This module decodes
and stores audio, resolves the expected units for both modes, runs the pipeline,
and persists sessions / feedback / corrections / progress snapshots. All AI and
storage are reached through the injected `pipeline` and `providers`.
"""

import base64
import binascii

from . import repository as repo
from .domain.goal_signature import GoalSignature
from .domain.pipeline import CoachingPipeline
from .domain.text import split_script_text
from .providers.registry import ProviderBundle


def resolve_expected_units(
    db, mode: str, script_id: str | None, script_text: str | None
) -> tuple[list[str] | None, str | None]:
    """Return (expected_units, resolved_script_id) for the session's mode.

    Guided mode reads the seeded script's lines; user-script mode splits the
    pasted text. Returns (None, None) when a guided script_id can't be found.
    """
    if mode == "guided":
        script = repo.get_script(db, script_id) if script_id else None
        if not script:
            return None, None
        lines = sorted(script.get("lines", []), key=lambda x: x["line_index"])
        return [ln["text"] for ln in lines], script_id
    units = split_script_text(script_text or "")
    return units, None


def store_utterances(
    providers: ProviderBundle, db, session_id: str, utterance_inputs, expected_units: list[str]
) -> None:
    """Decode + store each utterance's audio (if any) and persist its record."""
    for u in utterance_inputs:
        audio_key = None
        if u.audio_base64:
            try:
                raw = base64.b64decode(u.audio_base64, validate=True)
            except (binascii.Error, ValueError):
                raw = b""
            audio_key = f"sessions/{session_id}/utterances/{u.line_index}.wav"
            providers.store.put(audio_key, raw)
        repo.add_utterance(
            db,
            {
                "utterance_id": f"{session_id}:{u.line_index}",
                "session_id": session_id,
                "line_index": u.line_index,
                "audio_key": audio_key,
            },
        )


def _expected_for(line_index: int, expected_units: list[str]) -> str:
    return expected_units[line_index] if 0 <= line_index < len(expected_units) else ""


def process_session(
    db,
    pipeline: CoachingPipeline,
    session: dict,
    parent_scores: dict[str, float] | None = None,
) -> dict:
    """Run the pipeline over a session's stored utterances and persist results.

    Returns the freshly-read session doc (status `scored` or `failed`). On a
    successful scored run, writes the feedback, correction cards, version stamp,
    and (when `parent_scores` is given) the delta + a progress snapshot.
    """
    session_id = session["session_id"]
    repo.update_session(db, session_id, {"status": "processing"})

    expected_units = session.get("expected_units", [])
    stored = repo.list_utterances(db, session_id)
    pipe_utterances = [
        {
            "line_index": u["line_index"],
            "audio_key": u.get("audio_key"),
            "expected_text": _expected_for(u["line_index"], expected_units),
        }
        for u in stored
    ]
    goal = GoalSignature.from_dict(session.get("goal_signature"))
    result = pipeline.run(
        session_id=session_id,
        goal=goal,
        expected_units=expected_units,
        utterances=pipe_utterances,
        parent_scores=parent_scores,
    )

    if result.status != "scored":
        return repo.update_session(
            db, session_id, {"status": result.status, "error": "no utterances recorded"}
        )

    repo.save_feedback(
        db,
        {
            "feedback_id": f"{session_id}:feedback",
            "session_id": session_id,
            "summary": result.feedback.summary,
            "read_aloud_text": result.feedback.read_aloud_text,
            "strengths": result.feedback.strengths,
            "improvements": [
                {
                    "capability": i.capability,
                    "message": i.message,
                    "severity": i.severity,
                    "line_index": i.line_index,
                }
                for i in result.feedback.improvements
            ],
            "capability_scores": result.capability_scores,
            "overall_score": result.overall_score,
            **result.versions,
        },
    )
    for c in result.corrections:
        repo.save_correction(
            db,
            {
                "correction_id": f"{session_id}:{c.line_index}",
                "session_id": session_id,
                "line_index": c.line_index,
                "focus_capability": c.focus_capability,
                "original_text": c.original_text,
                "corrected_text": c.corrected_text,
                "explanation": c.explanation,
                "user_audio_key": c.user_audio_key,
                "ideal_audio_key": c.ideal_audio_key,
            },
        )

    update = {
        "status": "scored",
        "overall_score": result.overall_score,
        "capability_scores": result.capability_scores,
        **result.versions,
    }
    if result.delta is not None:
        update["delta"] = result.delta
        repo.save_progress_snapshot(
            db,
            {
                "snapshot_id": f"{session_id}:snapshot",
                "user_id": session["user_id"],
                "session_id": session_id,
                "overall_score": result.overall_score,
                "capability_scores": result.capability_scores,
                "delta_vs_previous": result.delta,
            },
        )
    return repo.update_session(db, session_id, update)


def assemble_detail(db, session: dict) -> dict:
    """Combine a session doc with its feedback + corrections into a detail dict."""
    feedback = repo.get_feedback(db, session["session_id"])
    corrections = repo.list_corrections(db, session["session_id"])
    versions = None
    if session.get("rubric_version"):
        versions = {
            "rubric_version": session.get("rubric_version"),
            "scoring_model_version": session.get("scoring_model_version"),
            "feature_extractor_version": session.get("feature_extractor_version"),
            "prompt_version": session.get("prompt_version"),
        }
    feedback_payload = None
    if feedback:
        feedback_payload = {
            "summary": feedback.get("summary", ""),
            "strengths": feedback.get("strengths", []),
            "improvements": feedback.get("improvements", []),
            "read_aloud_text": feedback.get("read_aloud_text", ""),
        }
    return {
        "session_id": session["session_id"],
        "user_id": session["user_id"],
        "mode": session["mode"],
        "status": session["status"],
        "script_id": session.get("script_id"),
        "expected_units": session.get("expected_units", []),
        "goal_signature": session.get("goal_signature") or {},
        "attempt": session.get("attempt", 1),
        "parent_session_id": session.get("parent_session_id"),
        "overall_score": session.get("overall_score"),
        "capability_scores": session.get("capability_scores") or {},
        "versions": versions,
        "feedback": feedback_payload,
        "corrections": corrections,
        "delta": session.get("delta"),
        "created_at": session.get("created_at"),
    }

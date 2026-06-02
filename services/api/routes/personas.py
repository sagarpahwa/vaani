"""Persona endpoints (20 Legends, Mode "persona"): list tiles + fetch full persona.

Read-only. The detail response exposes the speech the learner will record and the
demo-relevant rubric slice (target pace band, expressiveness, pause style); the
scoring weights and feedback notes stay server-side.
"""

from fastapi import APIRouter, Depends, HTTPException

from .. import repository as repo
from ..deps import get_db
from ..models import (
    PersonaDetail,
    PersonaReference,
    PersonaRubricView,
    PersonaSummary,
    ScriptLineModel,
)

router = APIRouter(tags=["personas"])


@router.get("/personas", response_model=list[PersonaSummary])
def list_personas(db=Depends(get_db)):
    return [
        PersonaSummary(
            persona_id=p["persona_id"],
            name=p["name"],
            role=p.get("role"),
            archetype=p.get("archetype"),
            line_count=len(p.get("speech", {}).get("lines", [])),
        )
        for p in repo.list_personas(db)
    ]


@router.get("/personas/{persona_id}", response_model=PersonaDetail)
def get_persona(persona_id: str, db=Depends(get_db)):
    p = repo.get_persona(db, persona_id)
    if not p:
        raise HTTPException(status_code=404, detail="persona not found")
    speech = p.get("speech", {})
    rubric = p.get("rubric", {})
    ref = p.get("reference") or {}
    return PersonaDetail(
        persona_id=p["persona_id"],
        name=p["name"],
        role=p.get("role"),
        archetype=p.get("archetype"),
        reference=PersonaReference(title=ref.get("title"), video_url=ref.get("video_url")),
        goal_line=p.get("goal_line"),
        signature_qualities=p.get("signature_qualities", []),
        estimated_duration_seconds=speech.get("estimated_duration_seconds"),
        lines=[ScriptLineModel(**ln) for ln in speech.get("lines", [])],
        rubric=PersonaRubricView(
            target_pace_sps=rubric.get("target_pace_sps", []),
            expressiveness=rubric.get("expressiveness"),
            pause_style=rubric.get("pause_style"),
        ),
    )

"""Guided-script endpoints (Mode A): list summaries and fetch full scripts."""

from fastapi import APIRouter, Depends, HTTPException

from .. import repository as repo
from ..deps import get_db
from ..models import ScriptDetail, ScriptSummary

router = APIRouter(tags=["scripts"])


@router.get("/scripts", response_model=list[ScriptSummary])
def list_scripts(db=Depends(get_db)):
    return [
        ScriptSummary(
            script_id=s["script_id"],
            title=s["title"],
            language=s.get("language"),
            difficulty=s.get("difficulty"),
            line_count=len(s.get("lines", [])),
        )
        for s in repo.list_scripts(db)
    ]


@router.get("/scripts/{script_id}", response_model=ScriptDetail)
def get_script(script_id: str, db=Depends(get_db)):
    script = repo.get_script(db, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="script not found")
    return ScriptDetail(**script)

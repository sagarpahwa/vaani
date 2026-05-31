"""WebSocket progress stream for a session's processing stages.

Processing in the POC is synchronous (done during the utterances POST), so this
stream emits the staged timeline a UI animates against, then a terminal `done`
event carrying the persisted status and overall score.
"""

from fastapi import APIRouter, WebSocket

from .. import repository as repo
from ..deps import get_db

router = APIRouter(tags=["events"])

STAGES = ["received", "transcribing", "analyzing", "scoring", "generating_feedback"]


@router.websocket("/sessions/{session_id}/events")
async def session_events(websocket: WebSocket, session_id: str):
    await websocket.accept()
    db = get_db(websocket)
    session = repo.get_session(db, session_id)
    if not session:
        await websocket.send_json({"stage": "error", "message": "session not found"})
        await websocket.close()
        return

    for stage in STAGES:
        await websocket.send_json({"stage": stage, "session_id": session_id})
    await websocket.send_json(
        {
            "stage": "done",
            "session_id": session_id,
            "status": session.get("status"),
            "overall_score": session.get("overall_score"),
        }
    )
    await websocket.close()

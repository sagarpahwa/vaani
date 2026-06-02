"""Audio streaming: serve a stored blob (user recording or ideal clip) by key."""

from fastapi import APIRouter, Depends, HTTPException, Response

from ..deps import get_providers

router = APIRouter(tags=["audio"])


@router.get("/audio/{key:path}")
def get_audio(key: str, providers=Depends(get_providers)):
    """Return the WAV bytes for `key` from the object store, or 404."""
    try:
        data = providers.store.get(key)
    except (KeyError, ValueError):
        raise HTTPException(status_code=404, detail="audio not found") from None
    return Response(content=data, media_type="audio/wav")

"""API routers for the coaching POC, aggregated for registration in app.py."""

from .audio import router as audio_router
from .events import router as events_router
from .scripts import router as scripts_router
from .sessions import router as sessions_router

all_routers = [scripts_router, sessions_router, audio_router, events_router]

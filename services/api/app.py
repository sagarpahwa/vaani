"""FastAPI application factory (POC)."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import Settings, get_settings
from .routes import all_routers


def create_app(settings: Settings | None = None, db=None, providers=None) -> FastAPI:
    """Build the app. `db`/`providers` are injectable for tests; left unset in
    production they are resolved lazily on first request (see `deps.py`)."""
    settings = settings or get_settings()

    app = FastAPI(
        title="Vaani Coaching API (POC)",
        version=__version__,
        summary="Universal public-speaking coaching backend — Mode A & Mode B.",
    )
    app.state.settings = settings
    app.state.db = db
    app.state.providers = providers

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )

    for router in all_routers:
        app.include_router(router)

    @app.get("/health", tags=["meta"])
    def health() -> dict:
        return {"status": "ok", "service": "vaani-coaching-api", "version": __version__}

    @app.get("/", tags=["meta"])
    def root() -> dict:
        return {"name": "Vaani Coaching API (POC)", "docs": "/docs", "health": "/health"}

    return app

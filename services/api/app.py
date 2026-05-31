"""FastAPI application factory (POC)."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    app = FastAPI(
        title="Vaani Coaching API (POC)",
        version=__version__,
        summary="Universal public-speaking coaching backend — Mode A & Mode B.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )

    @app.get("/health", tags=["meta"])
    def health() -> dict:
        return {"status": "ok", "service": "vaani-coaching-api", "version": __version__}

    @app.get("/", tags=["meta"])
    def root() -> dict:
        return {"name": "Vaani Coaching API (POC)", "docs": "/docs", "health": "/health"}

    return app

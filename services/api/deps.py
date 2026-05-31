"""FastAPI dependencies: settings, mock DB, providers, pipeline.

Resolved lazily from `app.state` so unit/contract tests can inject a mongomock
DB and an in-memory object store via `create_app(db=..., providers=...)` without
ever opening a real Mongo connection. Production (`main.py`) leaves them unset,
so the first request connects to the isolated mock DB (guarded by
`assert_mock_target`) and builds the LocalFS provider stack.
"""

from fastapi import Request

from .config import Settings, get_settings
from .domain.pipeline import CoachingPipeline
from .providers.registry import ProviderBundle, build_providers


def settings_dep(request: Request) -> Settings:
    return getattr(request.app.state, "settings", None) or get_settings()


def get_db(request: Request):
    """Return the app's Mongo database, connecting to the mock DB on first use."""
    db = getattr(request.app.state, "db", None)
    if db is None:
        from pymongo import MongoClient

        from .db.init_mock_db import assert_mock_target

        settings = settings_dep(request)
        assert_mock_target(settings.poc_mongo_uri, settings.poc_mongo_db)
        client = MongoClient(settings.poc_mongo_uri, serverSelectionTimeoutMS=5000)
        db = client[settings.poc_mongo_db]
        request.app.state.db = db
    return db


def get_providers(request: Request) -> ProviderBundle:
    providers = getattr(request.app.state, "providers", None)
    if providers is None:
        providers = build_providers(settings_dep(request))
        request.app.state.providers = providers
    return providers


def get_pipeline(request: Request) -> CoachingPipeline:
    return CoachingPipeline(get_providers(request))

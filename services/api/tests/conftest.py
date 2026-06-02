"""Ensure the repo root is importable so `services.api.*` resolves regardless of CWD."""

import sys
from pathlib import Path

import mongomock
import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class MockSettings:
    """Settings stand-in for the all-mock, in-memory test stack."""

    provider_stt = "mock"
    provider_tts = "mock"
    provider_llm = "mock"
    object_store = "memory"
    poc_storage_dir = "./.poc-storage"
    cors_origin_list = ["*"]


@pytest.fixture
def db():
    """In-memory mongomock database — no Docker, no network."""
    client = mongomock.MongoClient()
    return client["public_speaking_intelligence_mock"]


@pytest.fixture
def seeded_db(db):
    """Mongomock DB with POC collections initialized and demo data seeded."""
    from services.api.db.init_mock_db import init_db
    from services.api.db.seed_mock import seed_all

    init_db(db, apply_validators=False)
    seed_all(db)
    return db


@pytest.fixture
def providers():
    """Deterministic mock provider bundle backed by an in-memory object store."""
    from services.api.providers.object_store import InMemoryObjectStore
    from services.api.providers.registry import build_providers

    return build_providers(MockSettings(), store=InMemoryObjectStore())


@pytest.fixture
def client(seeded_db, providers):
    """TestClient wired to the seeded mongomock DB + mock providers (no network)."""
    from fastapi.testclient import TestClient

    from services.api.app import create_app

    app = create_app(settings=MockSettings(), db=seeded_db, providers=providers)
    return TestClient(app)

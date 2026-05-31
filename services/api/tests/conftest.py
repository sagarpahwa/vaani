"""Ensure the repo root is importable so `services.api.*` resolves regardless of CWD."""

import sys
from pathlib import Path

import mongomock
import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def db():
    """In-memory mongomock database — no Docker, no network."""
    client = mongomock.MongoClient()
    return client["public_speaking_intelligence_mock"]

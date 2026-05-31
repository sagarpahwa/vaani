import sys
from pathlib import Path

import mongomock
import pytest

# ── mongomock compatibility patch ──────────────────────────────────────────────
# pymongo >= 4.5 passes `sort=None` to BulkOperationBuilder.add_update(),
# but mongomock 4.3.0 doesn't declare that parameter. Patch it to absorb
# unknown kwargs so unit tests work without a real MongoDB.
from mongomock.collection import BulkOperationBuilder

_orig_add_update = BulkOperationBuilder.add_update


def _patched_add_update(self, selector, doc, multi=False, upsert=False,
                        collation=None, array_filters=None, hint=None, **_ignored):
    return _orig_add_update(self, selector, doc, multi=multi, upsert=upsert,
                            collation=collation, array_filters=array_filters, hint=hint)


BulkOperationBuilder.add_update = _patched_add_update  # type: ignore[method-assign]

# Add scripts/python to path so tests import directly (seed_speakers, utils.*, etc.)
sys.path.insert(0, str(Path(__file__).parents[1] / "scripts" / "python"))

VALID_SPEAKER = {
    "canonical_name": "Test Speaker",
    "slug": "test-speaker",
    "era": "contemporary",
    "living_status": "living",
    "country_or_region": "United States",
    "profession": "Coach",
    "profession_category": "educator",
    "overall_speaker_score": 0.75,
    "greatness_score": 0.70,
    "ethical_alignment_score": 0.90,
    "speaking_capabilities": [{"capability_id": "vocal_command", "strength_score": 0.8}],
    "schema_version": "1.0",
}

VALID_CAPABILITY = {
    "capability_id": "test_cap",
    "label": "Test Capability",
    "definition": "A definition with sufficient length for validation purposes.",
    "trainable": True,
    "parent_category": "delivery",
}

VALID_PROFESSION = {
    "profession_id": "test_profession",
    "label": "Test Profession",
}


@pytest.fixture
def mongo_client():
    client = mongomock.MongoClient()
    yield client
    client.close()


@pytest.fixture
def db(mongo_client):
    return mongo_client["test_vaani"]


@pytest.fixture
def valid_speaker():
    return dict(VALID_SPEAKER)


@pytest.fixture
def valid_capability():
    return dict(VALID_CAPABILITY)


@pytest.fixture
def valid_profession():
    return dict(VALID_PROFESSION)

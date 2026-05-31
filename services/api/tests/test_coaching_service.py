"""Unit tests for the service layer: expected-unit resolution + audio storage."""

from services.api import repository as repo
from services.api.coaching_service import resolve_expected_units, store_utterances
from services.api.models import UtteranceInput


def test_resolve_guided_returns_script_lines(seeded_db):
    units, script_id = resolve_expected_units(seeded_db, "guided", "self-intro-60s", None)
    assert script_id == "self-intro-60s"
    assert units and all(isinstance(u, str) for u in units)


def test_resolve_guided_missing_returns_none(seeded_db):
    assert resolve_expected_units(seeded_db, "guided", "nope", None) == (None, None)


def test_resolve_user_script_splits_text(db):
    units, script_id = resolve_expected_units(db, "user_script", None, "One thing.\nTwo thing.")
    assert units == ["One thing.", "Two thing."]
    assert script_id is None


def test_store_utterances_persists_and_handles_bad_base64(db, providers):
    store_utterances(
        providers,
        db,
        "s1",
        [
            UtteranceInput(line_index=0, audio_base64="!!!not-valid-base64!!!"),
            UtteranceInput(line_index=1, audio_base64=None),
        ],
        ["hello", "world"],
    )
    items = repo.list_utterances(db, "s1")
    assert len(items) == 2
    # Bad base64 still produced a stored (empty) blob with a key.
    assert items[0]["audio_key"] == "sessions/s1/utterances/0.wav"
    assert providers.store.exists(items[0]["audio_key"])
    # No audio supplied → no key.
    assert items[1]["audio_key"] is None

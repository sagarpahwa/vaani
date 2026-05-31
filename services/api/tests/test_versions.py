"""Tests for the pipeline version stamps (Mode A/B + persona path).

Both stamps must carry the same four keys (so persistence and the response model
stay path-agnostic), but their values must differ — that independence is what
lets a persona-scoring change be reviewed via its own golden without disturbing
the Mode A/B golden, and vice versa.
"""

from services.api.domain.versions import persona_version_stamp, version_stamp

_KEYS = {
    "rubric_version",
    "scoring_model_version",
    "feature_extractor_version",
    "prompt_version",
}


def test_both_stamps_have_the_same_four_keys():
    assert set(version_stamp()) == _KEYS
    assert set(persona_version_stamp()) == _KEYS


def test_persona_stamp_values_differ_from_mode_ab():
    ab = version_stamp()
    persona = persona_version_stamp()
    for k in _KEYS:
        assert ab[k] != persona[k], f"{k} must differ so the goldens stay independent"


def test_persona_versions_are_nonempty_strings():
    for v in persona_version_stamp().values():
        assert isinstance(v, str) and v

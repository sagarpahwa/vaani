"""Tests for the acoustic feature contract + analyzer interface.

The mock and real analyzer behavior tests land with P2.4/P2.5; this starts with
the type contract — ``AcousticFeatures`` construction/serialization and the
``AcousticAnalyzer`` ABC guard — which CI can cover (no numpy/PyAV needed).
"""

import pytest

from services.api.domain.types import AcousticFeatures
from services.api.providers.base import AcousticAnalyzer

_ALL_FIELDS = {
    "duration_s",
    "speech_rate_sps",
    "articulation_rate_sps",
    "est_syllables",
    "expected_syllables",
    "coverage_ratio",
    "pause_count",
    "pause_total_s",
    "longest_pause_s",
    "pause_positions",
    "pitch_range_semitones",
    "pitch_variation",
    "energy_variation",
    "voiced_ratio",
}


def test_acoustic_features_default_to_zero():
    f = AcousticFeatures()
    assert f.duration_s == 0.0
    assert f.est_syllables == 0
    assert f.pause_positions == []


def test_acoustic_features_to_dict_round_trips_and_listifies_pauses():
    f = AcousticFeatures(
        duration_s=3.0,
        speech_rate_sps=3.2,
        articulation_rate_sps=4.0,
        est_syllables=10,
        expected_syllables=12,
        coverage_ratio=10 / 12,
        pause_count=2,
        pause_total_s=0.8,
        longest_pause_s=0.5,
        pause_positions=[(1.0, 1.3), (2.0, 2.5)],
        pitch_range_semitones=7.5,
        pitch_variation=2.1,
        energy_variation=0.4,
        voiced_ratio=0.7,
    )
    d = f.to_dict()
    assert set(d) == _ALL_FIELDS
    assert d["speech_rate_sps"] == 3.2
    # tuples serialize to lists so the payload is JSON-friendly for API/golden.
    assert d["pause_positions"] == [[1.0, 1.3], [2.0, 2.5]]


def test_acoustic_analyzer_cannot_be_instantiated():
    # An ABC with an unimplemented abstractmethod must not be constructable.
    with pytest.raises(TypeError):
        AcousticAnalyzer()

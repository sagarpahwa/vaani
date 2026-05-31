"""Tests for the acoustic feature contract + analyzer interface.

The mock and real analyzer behavior tests land with P2.4/P2.5; this starts with
the type contract — ``AcousticFeatures`` construction/serialization and the
``AcousticAnalyzer`` ABC guard — which CI can cover (no numpy/PyAV needed).
"""

import pytest

from services.api.domain.text import estimate_syllables
from services.api.domain.types import AcousticFeatures
from services.api.providers.acoustic import MockAcousticAnalyzer
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


# ---- MockAcousticAnalyzer (the CI/golden default) --------------------------

_LINE = "Build suspense, then reveal with simple confident contrast."


def test_mock_is_an_acoustic_analyzer():
    assert isinstance(MockAcousticAnalyzer(), AcousticAnalyzer)


def test_mock_is_deterministic_for_same_input():
    a = MockAcousticAnalyzer().analyze(b"audio-a", expected_text=_LINE, seed=7)
    b = MockAcousticAnalyzer().analyze(b"audio-b", expected_text=_LINE, seed=7)
    # Same (text, seed) ⇒ identical features regardless of the bytes' content —
    # this is what keeps the golden stable across different real recordings.
    assert a.to_dict() == b.to_dict()


def test_mock_varies_by_expected_text():
    a = MockAcousticAnalyzer().analyze(b"x", expected_text=_LINE, seed=1)
    b = MockAcousticAnalyzer().analyze(b"x", expected_text="A different line entirely.", seed=1)
    assert a.to_dict() != b.to_dict()


def test_mock_full_read_has_unit_coverage_and_plausible_rate():
    f = MockAcousticAnalyzer().analyze(b"recorded", expected_text=_LINE, seed=3)
    assert f.expected_syllables == estimate_syllables(_LINE)
    assert f.est_syllables == f.expected_syllables
    assert f.coverage_ratio == 1.0
    assert 2.7 <= f.speech_rate_sps <= 3.9  # centered ~3.3 with bounded jitter
    assert f.articulation_rate_sps > f.speech_rate_sps
    assert 1 <= f.pause_count <= 3
    assert 0.6 <= f.voiced_ratio <= 0.85
    assert f.duration_s > 0
    assert len(f.pause_positions) == 1


def test_mock_empty_recording_is_a_skipped_line():
    f = MockAcousticAnalyzer().analyze(b"", expected_text=_LINE, seed=3)
    assert f.expected_syllables == estimate_syllables(_LINE)
    assert f.est_syllables == 0
    assert f.coverage_ratio == 0.0
    assert f.speech_rate_sps == 0.0
    assert f.pause_positions == []


def test_mock_storage_key_string_is_not_audio():
    # A non-bytes ref (e.g. an object-store key) is the no-real-audio path.
    f = MockAcousticAnalyzer().analyze("sessions/s1/0.wav", expected_text=_LINE, seed=3)
    assert f.coverage_ratio == 0.0

"""Tests for the real librosa acoustic analyzer, on synthetic signals.

librosa/scipy/soundfile are demo-machine-only deps, so this whole module skips
when librosa is absent (CI) — the same stance ``test_audio_decode.py`` takes. The
fixtures are Hann-windowed tone bursts (each burst ≈ one syllable nucleus)
separated by silence, so the measurement core can be checked without recording a
real voice. The key test is *fast vs slow*: the same content read faster yields a
higher measured pace — proof the engine judges the actual waveform, not text.
"""

import pytest

pytest.importorskip("librosa")
np = pytest.importorskip("numpy")

from services.api.providers.acoustic_librosa import LibrosaAcousticAnalyzer  # noqa: E402

_SR = 16000


def _bursts(
    n: int,
    *,
    burst_s: float = 0.18,
    gap_s: float = 0.22,
    freq: float = 200.0,
    lead_s: float = 0.1,
) -> "np.ndarray":
    """``n`` syllable-like tone bursts (Hann-enveloped) separated by silence."""
    burst_len = int(burst_s * _SR)
    win = np.hanning(burst_len).astype(np.float32)
    t = np.arange(burst_len) / _SR
    tone = (0.6 * np.sin(2 * np.pi * freq * t)).astype(np.float32) * win
    gap = np.zeros(int(gap_s * _SR), dtype=np.float32)
    lead = np.zeros(int(lead_s * _SR), dtype=np.float32)
    parts: list[np.ndarray] = [lead]
    for k in range(n):
        parts.append(tone)
        if k < n - 1:
            parts.append(gap)
    parts.append(lead)
    return np.concatenate(parts)


def test_detects_syllable_nuclei_pauses_and_steady_pitch():
    pcm = _bursts(5)  # five "syllables"
    f = LibrosaAcousticAnalyzer().analyze_pcm(pcm, _SR, expected_text="one two three four five")
    assert 3 <= f.est_syllables <= 7  # ~5 nuclei, generous DSP slack
    assert f.pause_count >= 2  # the inter-burst silences are real breaks
    assert f.longest_pause_s >= 0.15
    assert 0.0 < f.speech_rate_sps < 8.0
    assert f.coverage_ratio > 0.0
    assert f.pitch_variation < 3.5  # a single steady tone is near-monotone
    assert 0.0 < f.voiced_ratio < 1.0  # speech mixed with the silent gaps


def test_faster_read_measures_a_higher_pace_than_slower_read():
    slow = _bursts(4, burst_s=0.22, gap_s=0.40)
    fast = _bursts(10, burst_s=0.10, gap_s=0.06)
    a = LibrosaAcousticAnalyzer()
    f_slow = a.analyze_pcm(slow, _SR, expected_text="four slow syllables here")
    f_fast = a.analyze_pcm(fast, _SR, expected_text="ten quick little syllables in a row now go")
    assert f_fast.speech_rate_sps > f_slow.speech_rate_sps
    assert f_slow.speech_rate_sps > 0.0


def test_pure_silence_reads_as_no_speech():
    silence = np.zeros(int(1.2 * _SR), dtype=np.float32)
    f = LibrosaAcousticAnalyzer().analyze_pcm(silence, _SR, expected_text="anything at all")
    assert f.est_syllables == 0
    assert f.speech_rate_sps == 0.0
    assert f.coverage_ratio == 0.0


def test_empty_pcm_yields_expected_syllables_only():
    f = LibrosaAcousticAnalyzer().analyze_pcm(
        np.zeros(0, dtype=np.float32), _SR, expected_text="hello world"
    )
    assert f.est_syllables == 0
    assert f.expected_syllables == 3  # hello(2) world(1)
    assert f.duration_s == 0.0


def test_analyze_bytes_guard_for_no_recording():
    # The bytes entrypoint: an empty recording is the missed-line path (no decode).
    f = LibrosaAcousticAnalyzer().analyze(b"", expected_text="hello world")
    assert f.est_syllables == 0
    assert f.expected_syllables == 3
    assert f.coverage_ratio == 0.0

"""Tests for the persona pipeline branch (P3.2): acoustic analysis + aggregation.

The headline guarantee is that the persona path **never calls STT** — it judges
the raw waveform, not a transcript. The aggregation tests pin the rules a coach
expects: pace is measured only over spoken lines, while a skipped line drags
coverage down (the transcript-free skip signal).
"""

from services.api.domain.persona import aggregate_acoustic
from services.api.domain.pipeline import CoachingPipeline
from services.api.domain.types import AcousticFeatures, Transcript, UtteranceAnalysis
from services.api.providers.object_store import InMemoryObjectStore
from services.api.providers.registry import build_providers


class _Settings:
    provider_stt = "mock"
    provider_tts = "mock"
    provider_llm = "mock"
    provider_acoustic = "mock"
    object_store = "memory"
    poc_storage_dir = "./.poc-storage"


class _SpySTT:
    """STT stand-in that fails loudly if the persona path ever transcribes."""

    def __init__(self) -> None:
        self.called = False

    def transcribe(self, audio_ref, *, expected_text, seed=0):  # noqa: ANN001
        self.called = True
        raise AssertionError("persona path must not call STT")


def _ua(idx: int, expected: str, **af) -> UtteranceAnalysis:
    return UtteranceAnalysis(
        line_index=idx,
        expected_text=expected,
        transcript=Transcript(text="", words=[], duration_seconds=af.get("duration_s", 0.0)),
        alignment=[],
        acoustic=AcousticFeatures(**af),
    )


# ---- pipeline branch: no STT, acoustic carried per line --------------------


def test_persona_analysis_never_calls_stt():
    providers = build_providers(_Settings(), store=InMemoryObjectStore())
    providers.stt = _SpySTT()
    pipe = CoachingPipeline(providers)
    analyses = pipe.analyze_utterances_acoustic(
        session_id="s1",
        expected_units=["Hello world here", "Second line now"],
        utterances=[{"line_index": 0}, {"line_index": 1}],
    )
    assert providers.stt.called is False
    assert len(analyses) == 2
    assert all(a.acoustic is not None for a in analyses)
    assert all(a.alignment == [] for a in analyses)  # no transcript alignment


def test_persona_analysis_measures_recorded_line_presence():
    providers = build_providers(_Settings(), store=InMemoryObjectStore())
    providers.store.put("k0", b"pretend-audio-bytes")
    pipe = CoachingPipeline(providers)
    analyses = pipe.analyze_utterances_acoustic(
        session_id="s1",
        expected_units=["hello world"],  # hello(2) world(1) → 3 syllables
        utterances=[{"line_index": 0, "audio_key": "k0"}],
    )
    a = analyses[0]
    assert a.acoustic.expected_syllables == 3
    assert a.acoustic.est_syllables == 3  # mock: audio present → full coverage
    assert a.acoustic.coverage_ratio == 1.0


# ---- aggregation rules -----------------------------------------------------


def test_aggregate_acoustic_profile_pace_is_syllables_over_duration():
    analyses = [
        _ua(
            0,
            "a b c",
            duration_s=1.0,
            est_syllables=3,
            expected_syllables=3,
            speech_rate_sps=3.0,
            coverage_ratio=1.0,
            pause_count=1,
            pause_total_s=0.2,
            longest_pause_s=0.2,
            pitch_variation=2.0,
        ),
        _ua(
            1,
            "d e",
            duration_s=1.0,
            est_syllables=2,
            expected_syllables=2,
            speech_rate_sps=2.0,
            coverage_ratio=1.0,
            pitch_variation=1.0,
        ),
    ]
    p = aggregate_acoustic(analyses)
    assert p.lines_recorded == 2
    assert p.lines_expected == 2
    assert p.duration_s == 2.0
    assert p.speech_rate_sps == 2.5  # 5 syllables / 2.0 s
    assert p.pause_count == 1
    assert p.longest_pause_s == 0.2
    assert p.coverage_ratio == 1.0
    assert p.pitch_variation == 1.5  # mean(2.0, 1.0)


def test_aggregate_skipped_line_lowers_coverage_but_not_pace():
    analyses = [
        _ua(
            0,
            "a b c",
            duration_s=1.0,
            est_syllables=3,
            expected_syllables=3,
            speech_rate_sps=3.0,
            coverage_ratio=1.0,
        ),
        _ua(1, "d e", duration_s=0.0, est_syllables=0, expected_syllables=2, coverage_ratio=0.0),
    ]
    p = aggregate_acoustic(analyses)
    assert p.lines_recorded == 1  # only the spoken line counts toward pace
    assert p.lines_expected == 2
    assert p.coverage_ratio == 0.5  # mean(1.0, 0.0) — the skip shows up
    assert p.speech_rate_sps == 3.0  # measured only over the spoken line


def test_aggregate_no_audio_is_zero_profile():
    analyses = [_ua(0, "a b", duration_s=0.0, expected_syllables=2, coverage_ratio=0.0)]
    p = aggregate_acoustic(analyses)
    assert p.lines_recorded == 0
    assert p.lines_expected == 1
    assert p.speech_rate_sps == 0.0
    assert p.coverage_ratio == 0.0

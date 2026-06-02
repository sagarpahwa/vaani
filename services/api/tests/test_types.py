"""Tests for the persona additions to the domain type contract (P3.1).

Covers the new acoustic aggregate + ``style_match`` fields and, crucially, that
``PipelineResult.to_dict()`` *omits* them on the Mode A/B path (both ``None``),
so existing responses and the frozen golden stay byte-for-byte unchanged.
"""

from services.api.domain.types import (
    AcousticFeatures,
    AcousticProfile,
    DeliveryFeatures,
    FeedbackResult,
    PipelineResult,
    ScoreResult,
    Transcript,
    UtteranceAnalysis,
)


def _empty_features() -> DeliveryFeatures:
    return DeliveryFeatures(
        word_count=0,
        expected_word_count=0,
        duration_seconds=0.0,
        words_per_minute=0.0,
        filler_count=0,
        filler_rate=0.0,
        accuracy=0.0,
        stumble_count=0,
        long_pause_count=0,
    )


def _result(**kw) -> PipelineResult:
    return PipelineResult(
        status="scored",
        overall_score=0.8,
        capability_scores={"pace": 0.8},
        features=_empty_features(),
        feedback=FeedbackResult(summary="", strengths=[], improvements=[], read_aloud_text=""),
        corrections=[],
        versions={},
        **kw,
    )


def test_acoustic_profile_defaults_zero():
    p = AcousticProfile()
    assert p.speech_rate_sps == 0.0
    assert p.lines_recorded == 0


def test_acoustic_profile_to_dict_has_all_fields():
    p = AcousticProfile(speech_rate_sps=3.2, pause_count=2, lines_recorded=5, lines_expected=6)
    d = p.to_dict()
    assert d["speech_rate_sps"] == 3.2
    assert d["pause_count"] == 2
    assert set(d) == {
        "speech_rate_sps",
        "articulation_rate_sps",
        "coverage_ratio",
        "pause_count",
        "pause_total_s",
        "longest_pause_s",
        "pitch_range_semitones",
        "pitch_variation",
        "energy_variation",
        "voiced_ratio",
        "duration_s",
        "lines_recorded",
        "lines_expected",
    }


def test_score_result_style_match_defaults_none():
    s = ScoreResult(overall_score=0.7, capabilities={}, weights={})
    assert s.style_match is None
    s2 = ScoreResult(overall_score=0.7, capabilities={}, weights={}, style_match=0.9)
    assert s2.style_match == 0.9


def test_utterance_analysis_acoustic_defaults_none():
    a = UtteranceAnalysis(
        line_index=0,
        expected_text="hi",
        transcript=Transcript(text="hi", words=[], duration_seconds=0.0),
        alignment=[],
    )
    assert a.acoustic is None
    a.acoustic = AcousticFeatures(est_syllables=3)
    assert a.acoustic.est_syllables == 3


def test_pipeline_result_to_dict_omits_persona_fields_on_mode_ab():
    # Mode A/B: no persona → keys must be absent so the golden stays unchanged.
    d = _result().to_dict()
    assert "style_match" not in d
    assert "acoustic" not in d


def test_pipeline_result_to_dict_includes_persona_fields_when_set():
    d = _result(style_match=0.82, acoustic=AcousticProfile(speech_rate_sps=3.0)).to_dict()
    assert d["style_match"] == 0.82
    assert d["acoustic"]["speech_rate_sps"] == 3.0

"""Tests for persona feedback + corrections (P3.5).

The promise these tests pin: every correction is grounded in a *real measured
event* on that exact line and voiced in the persona's words. A too-fast line
names the syllable rate; a stall names the pause seconds; a skipped line names
how many syllables dropped — all read from the waveform, never a transcript.
"""

from services.api.domain.persona import PersonaRubric, build_persona_feedback
from services.api.domain.types import (
    AcousticFeatures,
    AcousticProfile,
    ScoreResult,
    Transcript,
    UtteranceAnalysis,
)


def _ua(idx: int, expected: str, **af) -> UtteranceAnalysis:
    return UtteranceAnalysis(
        line_index=idx,
        expected_text=expected,
        transcript=Transcript(text="", words=[], duration_seconds=af.get("duration_s", 0.0)),
        alignment=[],
        audio_key=f"k{idx}",
        acoustic=AcousticFeatures(**af),
    )


def _clean(idx: int, **over) -> UtteranceAnalysis:
    """An in-band, expressive, pause-free line — should never be flagged."""
    base = dict(
        duration_s=4.0,
        speech_rate_sps=3.1,
        est_syllables=12,
        expected_syllables=12,
        coverage_ratio=1.0,
        pause_count=0,
        longest_pause_s=0.2,
        pitch_variation=2.0,
        energy_variation=0.4,
    )
    base.update(over)
    return _ua(idx, "a clean spoken line here", **base)


def _rubric(**kw) -> PersonaRubric:
    base = dict(
        capability_weights={},
        target_pace_sps=(2.8, 3.6),
        expressiveness="high-contrast",
        pause_style="steady",
        feedback_notes={
            "too_fast": "You rushed the reveal.",
            "too_slow": "Let it breathe more.",
            "hesitation": "Hold the line, don't stall.",
            "monotone": "Vary your tone on the key beat.",
            "on_target": "Right in the pocket.",
        },
    )
    base.update(kw)
    return PersonaRubric(**base)


def _scores(**kw) -> ScoreResult:
    base = dict(overall_score=0.7, capabilities={"pace": 0.9, "fluency": 0.5}, weights={})
    base.update(kw)
    return ScoreResult(**base)


def _profile(**kw) -> AcousticProfile:
    base = dict(speech_rate_sps=3.1, lines_recorded=1, lines_expected=1)
    base.update(kw)
    return AcousticProfile(**base)


def test_too_fast_line_correction_cites_real_rate():
    analyses = [_clean(0, speech_rate_sps=6.0)]
    _, corrections = build_persona_feedback(
        persona_name="Steve Jobs",
        profile=_profile(speech_rate_sps=6.0),
        scores=_scores(),
        analyses=analyses,
        rubric=_rubric(),
    )
    assert len(corrections) == 1
    c = corrections[0]
    assert c.focus_capability == "pace"
    assert c.line_index == 0
    assert "6.0 syll/s" in c.explanation
    assert "You rushed the reveal." in c.explanation  # persona voice


def test_hesitation_line_cites_pause_seconds():
    analyses = [_clean(0, longest_pause_s=2.4)]
    _, corrections = build_persona_feedback(
        persona_name="Steve Jobs",
        profile=_profile(),
        scores=_scores(),
        analyses=analyses,
        rubric=_rubric(),
    )
    assert corrections[0].focus_capability == "fluency"
    assert "2.4s stall" in corrections[0].explanation


def test_skipped_line_flags_coverage_without_transcript():
    analyses = [
        _ua(
            0,
            "a five word line here",
            duration_s=0.0,
            est_syllables=0,
            expected_syllables=5,
            coverage_ratio=0.0,
        )
    ]
    _, corrections = build_persona_feedback(
        persona_name="Steve Jobs",
        profile=_profile(),
        scores=_scores(),
        analyses=analyses,
        rubric=_rubric(),
    )
    assert corrections[0].focus_capability == "clarity"
    assert "0 of 5" in corrections[0].explanation


def test_monotone_line_flagged_for_expressive_persona():
    analyses = [_clean(0, pitch_variation=0.3)]
    _, corrections = build_persona_feedback(
        persona_name="Brené Brown",
        profile=_profile(),
        scores=_scores(),
        analyses=analyses,
        rubric=_rubric(expressiveness="high-contrast"),
    )
    assert corrections[0].focus_capability == "engagement"
    assert "Vary your tone" in corrections[0].explanation


def test_clean_line_produces_no_correction():
    feedback, corrections = build_persona_feedback(
        persona_name="Steve Jobs",
        profile=_profile(),
        scores=_scores(),
        analyses=[_clean(0)],
        rubric=_rubric(),
    )
    assert corrections == []
    assert "nothing major" in feedback.summary


def test_corrections_capped_at_three_and_sorted_by_severity():
    analyses = [
        _clean(0, speech_rate_sps=6.0),  # too_fast (medium)
        _clean(1, pitch_variation=0.3),  # monotone (low)
        _clean(2, longest_pause_s=2.4),  # hesitation (high)
        _ua(
            3,
            "dropped line",
            duration_s=0.0,
            est_syllables=0,
            expected_syllables=4,
            coverage_ratio=0.0,
        ),  # skipped (high)
        _clean(4, speech_rate_sps=1.0),  # too_slow (medium)
    ]
    _, corrections = build_persona_feedback(
        persona_name="Steve Jobs",
        profile=_profile(),
        scores=_scores(),
        analyses=analyses,
        rubric=_rubric(),
    )
    assert len(corrections) == 3  # capped
    # The two high-severity lines (hesitation, skipped) come first.
    assert {corrections[0].focus_capability, corrections[1].focus_capability} == {
        "fluency",
        "clarity",
    }
    # The low-severity monotone line is dropped from the top 3.
    assert all(c.focus_capability != "engagement" for c in corrections)


def test_summary_names_persona_and_style_match():
    feedback, _ = build_persona_feedback(
        persona_name="Warren Buffett",
        profile=_profile(),
        scores=_scores(style_match=0.82),
        analyses=[_clean(0)],
        rubric=_rubric(),
    )
    assert "Warren Buffett" in feedback.summary
    assert "82%" in feedback.summary


def test_correction_carries_line_audio_key_for_ab_playback():
    _, corrections = build_persona_feedback(
        persona_name="Steve Jobs",
        profile=_profile(),
        scores=_scores(),
        analyses=[_clean(2, speech_rate_sps=6.0)],
        rubric=_rubric(),
    )
    c = corrections[0]
    assert c.user_audio_key == "k2"
    assert c.corrected_text == c.original_text  # ideal clip re-reads the same line

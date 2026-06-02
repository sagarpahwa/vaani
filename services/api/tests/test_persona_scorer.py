"""Tests for the persona scorer (P3.3): capabilities from acoustics vs a rubric.

The headline guarantee is *per-persona* scoring: an identical fast read scores
full marks against a fast speaker's band (Huang) but is docked against a slow
speaker's band (Buffett) — proving the score judges the waveform against *this
speaker*, not a global ideal. ``style_match`` is intentionally ``None`` here; it
is computed by a separate step (P3.4).
"""

from services.api.domain.goal_signature import CANONICAL_CAPABILITIES
from services.api.domain.persona import PersonaRubric, score_persona
from services.api.domain.types import AcousticProfile


def _profile(**kw) -> AcousticProfile:
    base = dict(
        speech_rate_sps=3.0,
        articulation_rate_sps=3.5,
        coverage_ratio=1.0,
        pause_count=2,
        pause_total_s=0.6,
        longest_pause_s=0.5,
        pitch_range_semitones=6.0,
        pitch_variation=1.8,
        energy_variation=0.4,
        voiced_ratio=0.7,
        duration_s=12.0,
        lines_recorded=4,
        lines_expected=4,
    )
    base.update(kw)
    return AcousticProfile(**base)


def _rubric(**kw) -> PersonaRubric:
    base = dict(
        capability_weights={c: 1.0 for c in CANONICAL_CAPABILITIES},
        target_pace_sps=(2.8, 3.6),
        expressiveness="balanced",
        pause_style="steady",
        feedback_notes={},
    )
    base.update(kw)
    return PersonaRubric(**base)


# ---- pace: the per-persona band ------------------------------------------


def test_pace_in_band_scores_full():
    s = score_persona(_profile(speech_rate_sps=3.0), _rubric(target_pace_sps=(2.8, 3.6)))
    assert s.capabilities["pace"] == 1.0


def test_pace_too_fast_scores_below_in_band():
    r = _rubric(target_pace_sps=(2.8, 3.6))
    in_band = score_persona(_profile(speech_rate_sps=3.0), r).capabilities["pace"]
    too_fast = score_persona(_profile(speech_rate_sps=5.5), r).capabilities["pace"]
    assert too_fast < in_band
    assert too_fast < 1.0


def test_same_fast_read_suits_fast_band_not_slow_band():
    # One identical fast read, judged against two different personas. This is the
    # whole point of persona scoring — the band, not the read, decides.
    fast_read = _profile(speech_rate_sps=4.5)
    huang = _rubric(target_pace_sps=(4.2, 5.0))  # fast/high-energy band
    buffett = _rubric(target_pace_sps=(2.4, 3.0))  # slow/steady band
    pace_for_huang = score_persona(fast_read, huang).capabilities["pace"]
    pace_for_buffett = score_persona(fast_read, buffett).capabilities["pace"]
    assert pace_for_huang == 1.0  # inside Huang's band
    assert pace_for_buffett < 0.75  # too fast for Buffett
    assert pace_for_huang > pace_for_buffett


# ---- the other capabilities ----------------------------------------------


def test_higher_coverage_raises_clarity():
    r = _rubric()
    low = score_persona(_profile(coverage_ratio=0.4), r).capabilities["clarity"]
    high = score_persona(_profile(coverage_ratio=1.0), r).capabilities["clarity"]
    assert high > low


def test_monotone_read_lowers_engagement_for_high_contrast():
    r = _rubric(expressiveness="high-contrast")
    monotone = score_persona(_profile(pitch_variation=0.4, energy_variation=0.1), r).capabilities[
        "engagement"
    ]
    expressive = score_persona(_profile(pitch_variation=3.0, energy_variation=0.5), r).capabilities[
        "engagement"
    ]
    assert expressive > monotone
    assert monotone < 0.4


def test_long_stall_lowers_fluency():
    r = _rubric(pause_style="steady")  # 1.2 s long-pause tolerance
    smooth = score_persona(_profile(longest_pause_s=0.5), r).capabilities["fluency"]
    stalled = score_persona(_profile(longest_pause_s=3.0), r).capabilities["fluency"]
    assert stalled < smooth


def test_capability_weights_shift_overall():
    # A read that's strong on pace but flat (weak engagement) scores higher for a
    # pace-weighted persona than for an engagement-weighted one.
    prof = _profile(speech_rate_sps=3.0, pitch_variation=0.2, energy_variation=0.1)
    base = {c: 1.0 for c in CANONICAL_CAPABILITIES}
    pace_heavy = _rubric(capability_weights={**base, "pace": 3.0})
    eng_heavy = _rubric(capability_weights={**base, "engagement": 3.0})
    assert (
        score_persona(prof, pace_heavy).overall_score > score_persona(prof, eng_heavy).overall_score
    )


# ---- rubric parsing -------------------------------------------------------


def test_from_dict_parses_real_rubric():
    d = {
        "capability_weights": {
            "clarity": 1.2,
            "pace": 1.3,
            "engagement": 1.3,
            "confidence": 1.2,
            "fluency": 0.8,
            "conciseness": 1.2,
        },
        "target_pace_sps": [2.8, 3.6],
        "expressiveness": "high-contrast",
        "pause_style": "dramatic",
        "feedback_notes": {"too_fast": "Slow the reveal."},
    }
    r = PersonaRubric.from_dict(d)
    assert r.target_pace_sps == (2.8, 3.6)
    assert r.expressiveness == "high-contrast"
    assert r.pause_style == "dramatic"
    assert r.capability_weights["pace"] == 1.3
    assert r.feedback_notes["too_fast"] == "Slow the reveal."


def test_from_dict_defaults_for_missing_fields():
    r = PersonaRubric.from_dict({})
    assert r.target_pace_sps == (2.5, 3.5)
    assert r.expressiveness == "balanced"
    assert r.pause_style == "steady"
    assert r.capability_weights == {}


# ---- invariants -----------------------------------------------------------


def test_all_scores_within_unit_interval_and_style_match_none():
    r = _rubric()
    extremes = [
        _profile(),
        _profile(
            speech_rate_sps=0.0,
            coverage_ratio=0.0,
            longest_pause_s=10.0,
            pause_count=20,
            articulation_rate_sps=12.0,
            pitch_variation=0.0,
            energy_variation=0.0,
        ),
        _profile(
            speech_rate_sps=9.0,
            coverage_ratio=1.0,
            pitch_variation=8.0,
            energy_variation=2.0,
        ),
    ]
    for prof in extremes:
        s = score_persona(prof, r)
        assert 0.0 <= s.overall_score <= 1.0
        for v in s.capabilities.values():
            assert 0.0 <= v <= 1.0
        assert set(s.capabilities) == set(CANONICAL_CAPABILITIES)
        assert s.style_match is None

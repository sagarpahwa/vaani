"""Tests for the persona ``style_match`` distance (P3.4).

``style_match`` answers "how much did you *sound like* this speaker" — a
two-directional distance, not an absolute quality score. The defining test is
that overshooting the persona is penalized: a very expressive read lowers the
match against a *monotone* persona, even though more expressiveness would raise
the absolute ``engagement`` capability. That asymmetry is what separates this
score from the capability scorer.
"""

from services.api.domain.goal_signature import CANONICAL_CAPABILITIES
from services.api.domain.persona import PersonaRubric, compute_style_match


def _profile(**kw):
    from services.api.domain.types import AcousticProfile

    base = dict(
        speech_rate_sps=3.2,
        articulation_rate_sps=3.6,
        coverage_ratio=1.0,
        pause_count=2,
        pause_total_s=0.6,
        longest_pause_s=1.2,
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


def test_matched_profile_scores_high():
    # In-band pace, on-target expressiveness, on-target pause length.
    s = compute_style_match(_profile(), _rubric())
    assert s > 0.9


def test_far_off_profile_scores_low():
    far = _profile(speech_rate_sps=6.0, pitch_variation=0.1, longest_pause_s=0.0)
    s = compute_style_match(far, _rubric())
    assert s < 0.4


def test_overexpressive_read_lowers_match_for_monotone_persona():
    # The asymmetry that distinguishes style_match from engagement: against a
    # monotone persona, being *more* expressive is a mismatch, not a bonus.
    r = _rubric(expressiveness="monotone")  # target 0.8 semitones
    matched = compute_style_match(_profile(pitch_variation=0.8), r)
    overexpressive = compute_style_match(_profile(pitch_variation=3.0), r)
    assert overexpressive < matched


def test_pace_out_of_band_lowers_match():
    r = _rubric(target_pace_sps=(2.4, 3.0))  # slow band
    in_band = compute_style_match(_profile(speech_rate_sps=2.7), r)
    too_fast = compute_style_match(_profile(speech_rate_sps=5.0), r)
    assert too_fast < in_band


def test_same_read_matches_one_persona_band_not_another():
    fast_read = _profile(speech_rate_sps=4.5, pitch_variation=2.5, longest_pause_s=0.8)
    huang = _rubric(target_pace_sps=(4.2, 5.0), expressiveness="high-contrast", pause_style="brisk")
    buffett = _rubric(target_pace_sps=(2.4, 3.0), expressiveness="balanced", pause_style="steady")
    assert compute_style_match(fast_read, huang) > compute_style_match(fast_read, buffett)


def test_style_match_within_unit_interval():
    r = _rubric()
    extremes = [
        _profile(),
        _profile(speech_rate_sps=0.0, pitch_variation=0.0, longest_pause_s=0.0),
        _profile(speech_rate_sps=12.0, pitch_variation=10.0, longest_pause_s=20.0),
    ]
    for prof in extremes:
        s = compute_style_match(prof, r)
        assert 0.0 <= s <= 1.0

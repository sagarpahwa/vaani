"""Persona-path pure logic: collapse per-line acoustics into a session profile.

The persona path scores the learner's *raw waveform*, never a transcript. This
module is the transcript-free half of that: given the per-line
``AcousticFeatures`` measured by the analyzer, it aggregates them into one
session-level ``AcousticProfile`` for the persona scorer and the feedback screen.

Aggregation rules (each chosen so the number means what a coach would expect):

* **Pace** is ``total syllables / total duration`` over *spoken* lines only — a
  skipped line (no audio) must not drag the measured rate toward zero.
* **Coverage** is the mean per-line ratio over *all expected* lines, so skipping
  a line *does* pull coverage down (that is exactly the skip signal).
* **Pauses** sum across lines; the longest pause is the session maximum.
* **Expressiveness** (pitch/energy) is the mean over spoken lines.
"""

from dataclasses import dataclass

from .goal_signature import CANONICAL_CAPABILITIES
from .types import (
    AcousticFeatures,
    AcousticProfile,
    CorrectionDraft,
    FeedbackResult,
    Improvement,
    ScoreResult,
    UtteranceAnalysis,
)


def aggregate_acoustic(analyses: list[UtteranceAnalysis]) -> AcousticProfile:
    """Collapse the per-line ``AcousticFeatures`` on ``analyses`` into one profile.

    Lines whose ``acoustic`` is missing are ignored; a line counts as *spoken*
    when it carries any audio duration (``duration_s > 0``). With no spoken line
    the profile is all-zero except ``lines_expected``.
    """
    feats = [a.acoustic for a in analyses if a.acoustic is not None]
    lines_expected = len(analyses)
    spoken = [f for f in feats if f.duration_s > 0]

    # Coverage spans every expected line (a skipped line contributes 0 → drags it down).
    coverage = (sum(f.coverage_ratio for f in feats) / len(feats)) if feats else 0.0

    if not spoken:
        return AcousticProfile(
            coverage_ratio=round(coverage, 3),
            lines_expected=lines_expected,
        )

    total_syll = sum(f.est_syllables for f in spoken)
    total_dur = sum(f.duration_s for f in spoken)
    total_pause = sum(f.pause_total_s for f in spoken)
    speech_time = max(total_dur - total_pause, 1e-6)
    n = len(spoken)

    return AcousticProfile(
        speech_rate_sps=round(total_syll / total_dur, 3) if total_dur > 0 else 0.0,
        articulation_rate_sps=round(total_syll / speech_time, 3),
        coverage_ratio=round(coverage, 3),
        pause_count=sum(f.pause_count for f in spoken),
        pause_total_s=round(total_pause, 3),
        longest_pause_s=round(max(f.longest_pause_s for f in spoken), 3),
        pitch_range_semitones=round(sum(f.pitch_range_semitones for f in spoken) / n, 3),
        pitch_variation=round(sum(f.pitch_variation for f in spoken) / n, 3),
        energy_variation=round(sum(f.energy_variation for f in spoken) / n, 3),
        voiced_ratio=round(sum(f.voiced_ratio for f in spoken) / n, 3),
        duration_s=round(total_dur, 3),
        lines_recorded=n,
        lines_expected=lines_expected,
    )


# ---- persona rubric + scorer ----------------------------------------------


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _band_score(value: float, lo: float, hi: float) -> float:
    """1.0 inside ``[lo, hi]``, decaying linearly to 0 as ``value`` leaves the band.

    The decay is scaled by the *near edge*, so it is symmetric in relative terms:
    a value 50% below ``lo`` and one 50% above ``hi`` both score 0.5. This is what
    makes the same read score differently against a fast vs a slow persona band.
    """
    if value <= 0:
        return 0.0
    if lo <= value <= hi:
        return 1.0
    if value < lo:
        return _clamp01(1.0 - (lo - value) / lo)
    return _clamp01(1.0 - (value - hi) / hi)


# How much pitch variation (semitones) counts as "fully expressive" per style.
_EXPRESSIVENESS_TARGET = {"monotone": 0.8, "balanced": 1.8, "high-contrast": 3.0}
# Pause tolerances per style — a dramatic speaker is *allowed* longer, denser pauses
# before fluency is docked; a brisk speaker is held to a tighter budget.
_PAUSE_TOL_LONG_S = {"steady": 1.2, "dramatic": 1.8, "brisk": 0.8}
_PAUSE_TOL_PER_LINE = {"steady": 0.9, "dramatic": 1.3, "brisk": 0.6}


@dataclass
class PersonaRubric:
    """The per-persona scoring contract, parsed from a persona's ``rubric`` block.

    ``capability_weights`` re-weights the six canonical capabilities; the band +
    style fields describe *this speaker's* delivery so the scorer judges against
    them rather than a global ideal. ``feedback_notes`` are the persona-voiced
    correction lines used downstream by the feedback step.
    """

    capability_weights: dict[str, float]
    target_pace_sps: tuple[float, float]
    expressiveness: str
    pause_style: str
    feedback_notes: dict[str, str]

    @classmethod
    def from_dict(cls, d: dict) -> "PersonaRubric":
        band = d.get("target_pace_sps") or [2.5, 3.5]
        lo, hi = float(band[0]), float(band[1])
        return cls(
            capability_weights=dict(d.get("capability_weights") or {}),
            target_pace_sps=(lo, hi),
            expressiveness=d.get("expressiveness", "balanced"),
            pause_style=d.get("pause_style", "steady"),
            feedback_notes=dict(d.get("feedback_notes") or {}),
        )


def score_persona(profile: AcousticProfile, rubric: PersonaRubric) -> ScoreResult:
    """Score the six canonical capabilities from *acoustics alone*, judged vs ``rubric``.

    No transcript is consulted — this is the "judge my voice, not a cleaned-up
    transcript" promise made concrete: pace is the measured syllable rate vs the
    persona's band, fluency/confidence come from the pause profile, engagement
    from pitch/energy variation vs the persona's expressiveness, and clarity/
    conciseness from line coverage. The persona's ``capability_weights`` then set
    the overall blend, so an identical read scores differently for a fast vs a
    slow speaker. ``style_match`` is left ``None`` here; it is computed separately.
    """
    lo, hi = rubric.target_pace_sps
    pace = _band_score(profile.speech_rate_sps, lo, hi)
    coverage = _clamp01(profile.coverage_ratio)

    tol_long = _PAUSE_TOL_LONG_S.get(rubric.pause_style, 1.2)
    tol_density = _PAUSE_TOL_PER_LINE.get(rubric.pause_style, 0.9)
    over_long = max(0.0, profile.longest_pause_s - tol_long)
    pauses_per_line = profile.pause_count / max(profile.lines_recorded, 1)
    over_density = max(0.0, pauses_per_line - tol_density)

    target_expr = _EXPRESSIVENESS_TARGET.get(rubric.expressiveness, 1.8)
    eng_pitch = _clamp01(profile.pitch_variation / target_expr) if target_expr > 0 else 0.0
    eng_energy = _clamp01(profile.energy_variation / 0.5)

    # A garbled sprint (very high articulation rate) costs clarity.
    fast_penalty = 0.1 * max(0.0, profile.articulation_rate_sps - 7.0)

    caps = {
        "clarity": _clamp01(0.30 + 0.70 * coverage - fast_penalty),
        "pace": pace,
        "fluency": _clamp01(1.0 - 0.35 * over_long - 0.25 * over_density),
        "confidence": _clamp01(0.35 + 0.45 * coverage + 0.20 * pace - 0.20 * over_long),
        "engagement": _clamp01(0.60 * eng_pitch + 0.40 * eng_energy),
        "conciseness": _clamp01(0.55 + 0.45 * coverage - 0.15 * over_density),
    }
    caps = {k: round(v, 4) for k, v in caps.items()}

    weights = rubric.capability_weights
    wtot = sum(weights.get(c, 1.0) for c in CANONICAL_CAPABILITIES)
    wsum = sum(caps[c] * weights.get(c, 1.0) for c in CANONICAL_CAPABILITIES)
    overall = round(wsum / wtot, 4) if wtot > 0 else 0.0

    return ScoreResult(overall_score=overall, capabilities=caps, weights=dict(weights))


def _relative_match(value: float, target: float) -> float:
    """1.0 when ``value`` equals ``target``, decaying to 0 as it diverges *either way*.

    This is the two-directional counterpart to the capability scorer: capabilities
    are mostly one-directional ("more expressive is fine"), but a style *match*
    docks you for overshooting the persona just as much as for undershooting.
    """
    if target <= 0:
        return 1.0 if value <= 0 else 0.0
    return _clamp01(1.0 - abs(value - target) / target)


def compute_style_match(profile: AcousticProfile, rubric: PersonaRubric) -> float:
    """A single 0–1 "how much you sounded like this speaker" score.

    Distinct from the capability scores: this is a *distance*, so being more
    expressive than a monotone persona, or pausing far longer than a brisk one,
    lowers it — even though those same traits might raise an absolute capability.
    Blends pace (in-band), expressiveness, and pause-length match, pace-weighted
    because the band is the most legible signature of a speaker's delivery.
    """
    lo, hi = rubric.target_pace_sps
    pace_match = _band_score(profile.speech_rate_sps, lo, hi)
    expr_match = _relative_match(
        profile.pitch_variation, _EXPRESSIVENESS_TARGET.get(rubric.expressiveness, 1.8)
    )
    pause_match = _relative_match(
        profile.longest_pause_s, _PAUSE_TOL_LONG_S.get(rubric.pause_style, 1.2)
    )
    score = 0.45 * pace_match + 0.35 * expr_match + 0.20 * pause_match
    return round(_clamp01(score), 4)


# ---- persona feedback: acoustic-grounded, per-line corrections -------------

# Each detectable line-level issue maps to the capability it hurts, the
# ``feedback_notes`` key that voices it, and its severity. Priority is the list
# order: a skipped line outranks a stall, which outranks pace, which outranks a
# flat read — we surface the single most actionable event per line.
_ISSUE_CAPABILITY = {
    "skipped": "clarity",
    "hesitation": "fluency",
    "too_fast": "pace",
    "too_slow": "pace",
    "monotone": "engagement",
}
_ISSUE_SEVERITY = {
    "skipped": "high",
    "hesitation": "high",
    "too_fast": "medium",
    "too_slow": "medium",
    "monotone": "low",
}
_SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}
_COVERAGE_SKIP_THRESHOLD = 0.6
_MAX_CORRECTIONS = 3


def _classify_line(af: AcousticFeatures, rubric: PersonaRubric) -> str | None:
    """The single dominant delivery problem on one line, judged vs the persona.

    Returns ``None`` for a clean line. Everything here is read off the waveform —
    coverage, pace, pause length, pitch movement — never a transcript.
    """
    lo, hi = rubric.target_pace_sps
    if af.duration_s <= 0 or af.coverage_ratio < _COVERAGE_SKIP_THRESHOLD:
        return "skipped"
    tol_long = _PAUSE_TOL_LONG_S.get(rubric.pause_style, 1.2)
    if af.longest_pause_s > tol_long + 0.6:
        return "hesitation"
    if af.speech_rate_sps > hi * 1.15:
        return "too_fast"
    if af.speech_rate_sps < lo * 0.85:
        return "too_slow"
    if rubric.expressiveness != "monotone":
        target_expr = _EXPRESSIVENESS_TARGET.get(rubric.expressiveness, 1.8)
        if af.pitch_variation < 0.4 * target_expr:
            return "monotone"
    return None


def _explain(issue: str, af: AcousticFeatures, rubric: PersonaRubric, persona_name: str) -> str:
    """The persona-voiced note plus the *measured* number that triggered it.

    The cited value is the whole point — a correction must name the real acoustic
    event ("ran at 5.1 syll/s", "a 2.4s stall") so the learner can trust it came
    from their actual recording, not a generic tip.
    """
    note = rubric.feedback_notes.get(issue, "")
    lo, hi = rubric.target_pace_sps
    if issue == "too_fast":
        detail = (
            f"You ran this line at {af.speech_rate_sps:.1f} syll/s — "
            f"above {persona_name}'s {lo:.1f}–{hi:.1f} band."
        )
    elif issue == "too_slow":
        detail = (
            f"This line crawled at {af.speech_rate_sps:.1f} syll/s — "
            f"below {persona_name}'s {lo:.1f}–{hi:.1f} band."
        )
    elif issue == "hesitation":
        detail = f"A {af.longest_pause_s:.1f}s stall broke the line."
    elif issue == "monotone":
        detail = (
            f"Pitch barely moved ({af.pitch_variation:.1f} semitones) — flat for {persona_name}."
        )
    elif issue == "skipped":
        detail = (
            f"Only {af.est_syllables} of {af.expected_syllables} expected syllables "
            f"landed — most of this line dropped."
        )
    else:
        detail = ""
    return f"{note} {detail}".strip()


def build_persona_feedback(
    *,
    persona_name: str,
    profile: AcousticProfile,
    scores: ScoreResult,
    analyses: list[UtteranceAnalysis],
    rubric: PersonaRubric,
) -> tuple[FeedbackResult, list[CorrectionDraft]]:
    """Persona feedback: a summary, strengths, and per-line A/B corrections.

    Each correction is grounded in a real, measured event on that exact line and
    voiced through the persona's ``feedback_notes``. The A/B ``corrected_text`` is
    the line itself, so the pipeline's ideal-clip TTS re-reads it well. Only the
    most actionable few lines become cards, sorted by severity.
    """
    scored: list[tuple[int, int, CorrectionDraft, Improvement]] = []
    for a in analyses:
        af = a.acoustic
        if af is None:
            continue
        issue = _classify_line(af, rubric)
        if issue is None:
            continue
        cap = _ISSUE_CAPABILITY[issue]
        sev = _ISSUE_SEVERITY[issue]
        explanation = _explain(issue, af, rubric, persona_name)
        draft = CorrectionDraft(
            line_index=a.line_index,
            focus_capability=cap,
            original_text=a.expected_text,
            corrected_text=a.expected_text,
            explanation=explanation,
            user_audio_key=a.audio_key,
        )
        imp = Improvement(
            capability=cap, message=explanation, severity=sev, line_index=a.line_index
        )
        scored.append((_SEVERITY_RANK[sev], a.line_index, draft, imp))

    scored.sort(key=lambda t: (t[0], t[1]))
    top = scored[:_MAX_CORRECTIONS]
    corrections = [t[2] for t in top]
    improvements = [t[3] for t in top]

    strengths = [
        f"Strong {cap} ({val:.0%})." for cap, val in scores.capabilities.items() if val >= 0.75
    ][:3]

    sm = scores.style_match
    sm_txt = f" Your style match to {persona_name} is {sm:.0%}." if sm is not None else ""
    if corrections:
        next_focus = f" Focus next on {corrections[0].focus_capability}."
    else:
        next_focus = " Clean delivery — nothing major to fix."
    summary = (
        f"You practiced like {persona_name} and scored {scores.overall_score:.0%} overall."
        f"{sm_txt}{next_focus}"
    )

    read_aloud = (
        f"{summary} Your overall pace was {profile.speech_rate_sps:.1f} syllables per second."
    )
    if corrections:
        read_aloud = f"{read_aloud} {corrections[0].explanation}"

    feedback = FeedbackResult(
        summary=summary,
        strengths=strengths,
        improvements=improvements,
        read_aloud_text=read_aloud,
    )
    return feedback, corrections

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

from .types import AcousticProfile, UtteranceAnalysis


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

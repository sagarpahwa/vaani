"""Dataclasses passed between pipeline stages.

These are the in-memory contract of the domain layer. They are deliberately
plain (no pydantic) so the pure logic stays dependency-light; the API layer
maps them to/from pydantic request/response models.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Word:
    """A single recognized token with timing and confidence."""

    word: str
    start: float
    end: float
    confidence: float


@dataclass
class Transcript:
    """STT output for one utterance: the joined text plus per-word timing."""

    text: str
    words: list[Word]
    duration_seconds: float


@dataclass
class AlignOp:
    """One edit-distance operation aligning reference (expected) to hypothesis."""

    op: str  # "match" | "sub" | "insert" | "delete"
    ref: str | None
    hyp: str | None


@dataclass
class UtteranceAnalysis:
    """Per-line analysis: the transcript aligned against its expected text.

    In the persona path ``acoustic`` carries the raw-waveform measurements for
    this line (pace/pauses/pitch), so a correction can cite the real event on the
    exact line. Mode A/B leave it ``None`` — they score from the transcript only.
    """

    line_index: int
    expected_text: str
    transcript: Transcript
    alignment: list[AlignOp]
    audio_key: str | None = None
    acoustic: AcousticFeatures | None = None


@dataclass
class DeliveryFeatures:
    """Aggregate acoustic/text features feeding the rubric scorer."""

    word_count: int
    expected_word_count: int
    duration_seconds: float
    words_per_minute: float
    filler_count: int
    filler_rate: float
    accuracy: float
    stumble_count: int
    long_pause_count: int


@dataclass
class AcousticFeatures:
    """Per-utterance measurements taken from the raw waveform — never a transcript.

    This is the heart of the "judge my speech, not a cleaned-up transcript" rule:
    every field is derived from the audio samples themselves. Pace comes from
    syllable-nuclei peaks on the intensity envelope, pauses from the energy
    contour, expressiveness from pitch (F0) and energy dynamics. ``expected_text``
    feeds only ``coverage_ratio`` (did a line get skipped/truncated), never the
    grading of wording. All fields default to zero so analyzers set them
    explicitly and scorer/style tests can build targeted partials.
    """

    duration_s: float = 0.0
    speech_rate_sps: float = 0.0  # syllables / total duration (incl. pauses)
    articulation_rate_sps: float = 0.0  # syllables / voiced time (excl. pauses)
    est_syllables: int = 0  # syllable nuclei detected in the audio
    expected_syllables: int = 0  # syllables in the expected line text
    coverage_ratio: float = 0.0  # est / expected (skipped line → well below 1)
    pause_count: int = 0  # silences longer than the pause threshold
    pause_total_s: float = 0.0
    longest_pause_s: float = 0.0
    pause_positions: list[tuple[float, float]] = field(default_factory=list)  # (start_s, end_s)
    pitch_range_semitones: float = 0.0  # p95 − p5 of F0, in semitones
    pitch_variation: float = 0.0  # F0 std in semitones (monotone ≈ 0)
    energy_variation: float = 0.0  # coefficient of variation of frame RMS
    voiced_ratio: float = 0.0  # fraction of frames carrying pitch

    def to_dict(self) -> dict:
        """Serialize to a JSON-friendly dict (tuples → lists) for API/golden use."""
        return {
            "duration_s": self.duration_s,
            "speech_rate_sps": self.speech_rate_sps,
            "articulation_rate_sps": self.articulation_rate_sps,
            "est_syllables": self.est_syllables,
            "expected_syllables": self.expected_syllables,
            "coverage_ratio": self.coverage_ratio,
            "pause_count": self.pause_count,
            "pause_total_s": self.pause_total_s,
            "longest_pause_s": self.longest_pause_s,
            "pause_positions": [list(p) for p in self.pause_positions],
            "pitch_range_semitones": self.pitch_range_semitones,
            "pitch_variation": self.pitch_variation,
            "energy_variation": self.energy_variation,
            "voiced_ratio": self.voiced_ratio,
        }


@dataclass
class AcousticProfile:
    """Session-level acoustic aggregate over the recorded lines (persona path).

    Per-line ``AcousticFeatures`` collapsed into one delivery profile: pace and
    expressiveness are duration-weighted means, pauses sum across lines, the
    longest pause is the session max, coverage is the mean per-line ratio. This
    is what the persona scorer compares against the speaker's target bands and
    what the feedback screen reads back ("your pace vs the target band"). All
    fields measured from audio — the expected text only ever bounds coverage.
    """

    speech_rate_sps: float = 0.0
    articulation_rate_sps: float = 0.0
    coverage_ratio: float = 0.0
    pause_count: int = 0
    pause_total_s: float = 0.0
    longest_pause_s: float = 0.0
    pitch_range_semitones: float = 0.0
    pitch_variation: float = 0.0
    energy_variation: float = 0.0
    voiced_ratio: float = 0.0
    duration_s: float = 0.0
    lines_recorded: int = 0
    lines_expected: int = 0

    def to_dict(self) -> dict:
        """JSON-friendly dict for the API/feedback layer."""
        return {
            "speech_rate_sps": self.speech_rate_sps,
            "articulation_rate_sps": self.articulation_rate_sps,
            "coverage_ratio": self.coverage_ratio,
            "pause_count": self.pause_count,
            "pause_total_s": self.pause_total_s,
            "longest_pause_s": self.longest_pause_s,
            "pitch_range_semitones": self.pitch_range_semitones,
            "pitch_variation": self.pitch_variation,
            "energy_variation": self.energy_variation,
            "voiced_ratio": self.voiced_ratio,
            "duration_s": self.duration_s,
            "lines_recorded": self.lines_recorded,
            "lines_expected": self.lines_expected,
        }


@dataclass
class ScoreResult:
    """Overall score plus per-capability breakdown and the weights used.

    ``style_match`` (0–1) is the persona path's "how close to this speaker"
    score — distance of the measured profile from the speaker's target bands. It
    is ``None`` for Mode A/B, which has no persona to match.
    """

    overall_score: float
    capabilities: dict[str, float]
    weights: dict[str, float]
    style_match: float | None = None


@dataclass
class Improvement:
    """A single actionable coaching note tied to a capability and line."""

    capability: str
    message: str
    severity: str  # "low" | "medium" | "high"
    line_index: int | None = None


@dataclass
class FeedbackResult:
    """Written feedback: summary, strengths, ranked improvements, read-aloud text."""

    summary: str
    strengths: list[str]
    improvements: list[Improvement]
    read_aloud_text: str


@dataclass
class CorrectionDraft:
    """An A/B correction card: user's line vs. an ideal re-delivery."""

    line_index: int
    focus_capability: str
    original_text: str
    corrected_text: str
    explanation: str
    user_audio_key: str | None = None
    ideal_audio_key: str | None = None


@dataclass
class PipelineResult:
    """The full output of one coaching run, ready to persist and return."""

    status: str
    overall_score: float
    capability_scores: dict[str, float]
    features: DeliveryFeatures
    feedback: FeedbackResult
    corrections: list[CorrectionDraft]
    versions: dict[str, str]
    delta: dict[str, float] | None = None
    analyses: list[UtteranceAnalysis] = field(default_factory=list)
    style_match: float | None = None  # persona path only
    acoustic: AcousticProfile | None = None  # persona path only

    def to_dict(self) -> dict:
        """Serialize to a plain dict for the API/response layer.

        ``style_match`` / ``acoustic`` are added only on the persona path (when
        set), so Mode A/B responses and the existing golden stay byte-for-byte
        unchanged.
        """
        out: dict = {
            "status": self.status,
            "overall_score": self.overall_score,
            "capability_scores": self.capability_scores,
            "features": {
                "word_count": self.features.word_count,
                "expected_word_count": self.features.expected_word_count,
                "duration_seconds": self.features.duration_seconds,
                "words_per_minute": self.features.words_per_minute,
                "filler_count": self.features.filler_count,
                "filler_rate": self.features.filler_rate,
                "accuracy": self.features.accuracy,
                "stumble_count": self.features.stumble_count,
                "long_pause_count": self.features.long_pause_count,
            },
            "feedback": {
                "summary": self.feedback.summary,
                "strengths": self.feedback.strengths,
                "improvements": [
                    {
                        "capability": imp.capability,
                        "message": imp.message,
                        "severity": imp.severity,
                        "line_index": imp.line_index,
                    }
                    for imp in self.feedback.improvements
                ],
                "read_aloud_text": self.feedback.read_aloud_text,
            },
            "corrections": [
                {
                    "line_index": c.line_index,
                    "focus_capability": c.focus_capability,
                    "original_text": c.original_text,
                    "corrected_text": c.corrected_text,
                    "explanation": c.explanation,
                    "user_audio_key": c.user_audio_key,
                    "ideal_audio_key": c.ideal_audio_key,
                }
                for c in self.corrections
            ],
            "versions": self.versions,
            "delta": self.delta,
        }
        if self.style_match is not None:
            out["style_match"] = self.style_match
        if self.acoustic is not None:
            out["acoustic"] = self.acoustic.to_dict()
        return out

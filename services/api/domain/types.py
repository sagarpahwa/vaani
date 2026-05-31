"""Dataclasses passed between pipeline stages.

These are the in-memory contract of the domain layer. They are deliberately
plain (no pydantic) so the pure logic stays dependency-light; the API layer
maps them to/from pydantic request/response models.
"""

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
    """Per-line analysis: the transcript aligned against its expected text."""

    line_index: int
    expected_text: str
    transcript: Transcript
    alignment: list[AlignOp]
    audio_key: str | None = None


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
class ScoreResult:
    """Overall score plus per-capability breakdown and the weights used."""

    overall_score: float
    capabilities: dict[str, float]
    weights: dict[str, float]


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

    def to_dict(self) -> dict:
        """Serialize to a plain dict for the API/response layer."""
        return {
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

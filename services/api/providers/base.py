"""Abstract interfaces every provider implementation must satisfy.

Swapping mock → cloud means writing a new subclass and registering it in
`registry.py`; no domain code changes. Keeping these ABCs narrow is what makes
the pipeline testable without any network or cloud SDK.
"""

from abc import ABC, abstractmethod

from ..domain.goal_signature import GoalSignature
from ..domain.types import (
    AcousticFeatures,
    AlignOp,
    CorrectionDraft,
    DeliveryFeatures,
    FeedbackResult,
    ScoreResult,
    Transcript,
    UtteranceAnalysis,
)

# Disfluencies the feature extractor counts as fillers. Lowercased, no punctuation.
FILLER_WORDS = frozenset({"um", "uh", "er", "ah", "like", "so", "basically", "actually"})


class STTProvider(ABC):
    """Speech-to-text: audio reference + expected text → timestamped transcript."""

    @abstractmethod
    def transcribe(
        self, audio_ref: bytes | str, *, expected_text: str, seed: int
    ) -> Transcript: ...


class AcousticAnalyzer(ABC):
    """Measures delivery acoustics from a raw mono PCM waveform — no transcript.

    The persona path scores *how the learner actually sounded* (pace, pauses,
    pitch, energy), so this consumes audio samples, not text. ``pcm`` is left
    unannotated on purpose: the real impl takes a numpy float32 array, but base.py
    must stay import-clean in CI (numpy is a demo-machine-only dep). ``expected_text``
    is used solely to compute syllable coverage (skip/truncation), never to grade
    wording.
    """

    @abstractmethod
    def analyze(
        self, pcm, sample_rate: int, *, expected_text: str, seed: int = 0
    ) -> AcousticFeatures: ...


class Aligner(ABC):
    """Aligns expected (reference) tokens to recognized (hypothesis) tokens."""

    @abstractmethod
    def align(self, expected: list[str], hypothesis: list[str]) -> list[AlignOp]: ...


class FeatureExtractor(ABC):
    """Derives aggregate delivery features from per-utterance analyses."""

    @abstractmethod
    def extract(self, analyses: list[UtteranceAnalysis]) -> DeliveryFeatures: ...


class Scorer(ABC):
    """Maps delivery features to per-capability scores and a weighted overall."""

    @abstractmethod
    def score(self, features: DeliveryFeatures, weights: dict[str, float]) -> ScoreResult: ...


class FeedbackGenerator(ABC):
    """Produces written feedback + A/B correction drafts from analysis + scores."""

    @abstractmethod
    def generate(
        self,
        *,
        features: DeliveryFeatures,
        scores: ScoreResult,
        analyses: list[UtteranceAnalysis],
        goal: GoalSignature,
    ) -> tuple[FeedbackResult, list[CorrectionDraft]]: ...


class TTSProvider(ABC):
    """Text-to-speech: text → audio bytes (used for ideal re-delivery clips)."""

    @abstractmethod
    def synthesize(self, text: str) -> bytes: ...


class ObjectStore(ABC):
    """Binary blob storage keyed by string. Audio never lives in Mongo docs."""

    @abstractmethod
    def put(self, key: str, data: bytes) -> str: ...

    @abstractmethod
    def get(self, key: str) -> bytes: ...

    @abstractmethod
    def exists(self, key: str) -> bool: ...

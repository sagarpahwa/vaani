"""Wires concrete providers together based on settings.

The deterministic mock stack is the default (and the only one CI/golden uses).
For a real demo, `PROVIDER_STT=whisper` (local faster-whisper), `PROVIDER_TTS=macos`
(macOS `say`), and `PROVIDER_ACOUSTIC=librosa` (real waveform delivery analysis for
the persona path) swap in real speech-to-text, text-to-speech, and acoustic scoring
— all no-cloud, no-credential, and imported lazily so their optional dependencies
never affect the mock path. Any unrecognized `PROVIDER_*` value fails loudly
(ValueError) rather than silently degrading, and `minio` object storage raises
NotImplementedError until wired — so a misconfiguration can never quietly fall
back to a half-working state.
"""

from dataclasses import dataclass

from .acoustic import MockAcousticAnalyzer
from .analysis import DeliveryFeatureExtractor, RubricScorer, SequenceAligner
from .base import (
    AcousticAnalyzer,
    Aligner,
    FeatureExtractor,
    FeedbackGenerator,
    ObjectStore,
    Scorer,
    STTProvider,
    TTSProvider,
)
from .mock_ai import MockFeedbackGenerator, MockSTT, MockTTS
from .object_store import InMemoryObjectStore, LocalFSObjectStore


@dataclass
class ProviderBundle:
    """The full set of providers one pipeline run needs."""

    stt: STTProvider
    aligner: Aligner
    feature_extractor: FeatureExtractor
    scorer: Scorer
    feedback: FeedbackGenerator
    tts: TTSProvider
    acoustic: AcousticAnalyzer
    store: ObjectStore


def _build_stt(settings) -> STTProvider:
    kind = getattr(settings, "provider_stt", "mock")
    if kind == "mock":
        return MockSTT()
    if kind == "whisper":
        from .whisper_stt import WhisperSTT  # lazy: optional faster-whisper dep

        return WhisperSTT(
            model_size=getattr(settings, "poc_whisper_model", "base.en"),
            device=getattr(settings, "poc_whisper_device", "cpu"),
            compute_type=getattr(settings, "poc_whisper_compute", "int8"),
        )
    raise ValueError(f"provider_stt={kind!r} is not supported; use 'mock' or 'whisper'.")


def _build_tts(settings) -> TTSProvider:
    kind = getattr(settings, "provider_tts", "mock")
    if kind == "mock":
        return MockTTS()
    if kind == "macos":
        from .macos_tts import MacSayTTS  # lazy: darwin-only `say`

        return MacSayTTS(
            voice=getattr(settings, "poc_tts_voice", "") or None,
            rate=getattr(settings, "poc_tts_rate", 0) or None,
        )
    raise ValueError(f"provider_tts={kind!r} is not supported; use 'mock' or 'macos'.")


def _build_acoustic(settings) -> AcousticAnalyzer:
    kind = getattr(settings, "provider_acoustic", "mock")
    if kind == "mock":
        return MockAcousticAnalyzer()
    if kind == "librosa":
        from .acoustic_librosa import LibrosaAcousticAnalyzer  # lazy: optional librosa dep

        return LibrosaAcousticAnalyzer()
    raise ValueError(f"provider_acoustic={kind!r} is not supported; use 'mock' or 'librosa'.")


def _build_store(kind: str, settings) -> ObjectStore:
    if kind == "localfs":
        root = getattr(settings, "poc_storage_dir", "./.poc-storage")
        return LocalFSObjectStore(root)
    if kind == "memory":
        return InMemoryObjectStore()
    if kind == "minio":
        raise NotImplementedError(
            "MinIO object store is not wired in the POC; use 'localfs' or 'memory'."
        )
    raise ValueError(f"unknown OBJECT_STORE: {kind!r}")


def build_providers(settings=None, store: ObjectStore | None = None) -> ProviderBundle:
    """Assemble a ProviderBundle from settings (defaults to the mock stack).

    `store` can be injected directly (tests pass an InMemoryObjectStore);
    otherwise it's constructed from `settings.object_store`.
    """
    if settings is None:
        from ..config import get_settings

        settings = get_settings()

    # Feedback generation has no real-LLM impl in the POC; it is always the
    # (now alignment-grounded) deterministic generator. STT/TTS can go real.
    llm = getattr(settings, "provider_llm", "mock")
    if llm != "mock":
        raise ValueError(f"provider_llm={llm!r} is not supported in the POC; only 'mock'.")

    if store is None:
        store = _build_store(getattr(settings, "object_store", "localfs"), settings)

    return ProviderBundle(
        stt=_build_stt(settings),
        aligner=SequenceAligner(),
        feature_extractor=DeliveryFeatureExtractor(),
        scorer=RubricScorer(),
        feedback=MockFeedbackGenerator(),
        tts=_build_tts(settings),
        acoustic=_build_acoustic(settings),
        store=store,
    )

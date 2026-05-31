"""Wires concrete providers together based on settings.

Only the deterministic mock stack is implemented in the POC. Selecting any other
`PROVIDER_*` value fails loudly (ValueError) rather than silently degrading, and
`minio` object storage raises NotImplementedError until wired — so a
misconfiguration can never quietly fall back to a half-working state.
"""

from dataclasses import dataclass

from .analysis import DeliveryFeatureExtractor, RubricScorer, SequenceAligner
from .base import (
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
    store: ObjectStore


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

    for name in ("provider_stt", "provider_tts", "provider_llm"):
        value = getattr(settings, name, "mock")
        if value != "mock":
            raise ValueError(
                f"{name}={value!r} is not supported in the POC; only 'mock' is implemented."
            )

    if store is None:
        store = _build_store(getattr(settings, "object_store", "localfs"), settings)

    return ProviderBundle(
        stt=MockSTT(),
        aligner=SequenceAligner(),
        feature_extractor=DeliveryFeatureExtractor(),
        scorer=RubricScorer(),
        feedback=MockFeedbackGenerator(),
        tts=MockTTS(),
        store=store,
    )

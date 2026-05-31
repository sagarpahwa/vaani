"""End-to-end persona-pipeline test (P3.9): a faster read scores differently.

Runs the whole persona path — analyze -> aggregate -> score -> style_match ->
result — and asserts that a faster measured read and a slower one of the *same*
speech, judged against the same fast-speaker band, yield a different pace and a
different ``style_match``, and that the slow read earns a per-line "too slow"
correction citing the real rate.

The deterministic mock analyzer derives its features from the line text, so it
cannot represent "the learner spoke faster". This test therefore injects a
rate-controlled analyzer to exercise exactly the speed signal the real
``librosa`` analyzer measures off the waveform — the property the demo turns on.
"""

from services.api.domain.persona import PersonaRubric
from services.api.domain.pipeline import CoachingPipeline
from services.api.domain.text import estimate_syllables
from services.api.domain.types import AcousticFeatures
from services.api.providers.base import AcousticAnalyzer
from services.api.providers.object_store import InMemoryObjectStore
from services.api.providers.registry import build_providers


class _Settings:
    provider_stt = "mock"
    provider_tts = "mock"
    provider_llm = "mock"
    provider_acoustic = "mock"
    object_store = "memory"
    poc_storage_dir = "./.poc-storage"


class _FixedRateAcoustic(AcousticAnalyzer):
    """Acoustic stand-in pinned to one measured syllable rate — a fast vs slow read.

    Duration is back-computed from the rate so the aggregated session pace equals
    ``speech_rate_sps``; everything else is held constant, so pace + style_match
    move *only* with the rate under test.
    """

    def __init__(self, speech_rate_sps: float):
        self.rate = speech_rate_sps

    def analyze(self, audio_ref, *, expected_text, seed=0):  # noqa: ANN001
        syll = estimate_syllables(expected_text) or 6
        duration = round(syll / self.rate, 3) if self.rate > 0 else 0.0
        return AcousticFeatures(
            duration_s=duration,
            speech_rate_sps=self.rate,
            articulation_rate_sps=round(self.rate + 0.5, 3),
            est_syllables=syll,
            expected_syllables=syll,
            coverage_ratio=1.0,
            pause_count=1,
            pause_total_s=0.3,
            longest_pause_s=0.3,
            pitch_range_semitones=6.0,
            pitch_variation=2.5,
            energy_variation=0.4,
            voiced_ratio=0.7,
        )


# A fast speaker's band (Huang-like): 4.6 sps sits inside it; 2.2 is far below.
_FAST_BAND_RUBRIC = PersonaRubric.from_dict(
    {
        "capability_weights": {
            "clarity": 1.0,
            "pace": 1.4,
            "engagement": 1.3,
            "confidence": 1.0,
            "fluency": 0.9,
            "conciseness": 1.0,
        },
        "target_pace_sps": [4.2, 5.0],
        "expressiveness": "high-contrast",
        "pause_style": "brisk",
        "feedback_notes": {"too_slow": "Lift the energy — this speaker drives hard."},
    }
)

_LINES = [
    "We just doubled the performance of every layer in the stack.",
    "And we did it in a single generation, not in five.",
    "This is the engine of the next industrial revolution.",
]


def _run_at_rate(rate: float):
    providers = build_providers(_Settings(), store=InMemoryObjectStore())
    providers.acoustic = _FixedRateAcoustic(rate)
    pipe = CoachingPipeline(providers)
    utterances = []
    for i in range(len(_LINES)):
        key = f"sessions/rate-{rate}/utterances/{i}.wav"
        providers.store.put(key, b"\x01" * 16)  # presence: the line counts as spoken
        utterances.append({"line_index": i, "audio_key": key})
    return pipe.run_persona(
        session_id=f"rate-{rate}",
        persona_name="Jensen Huang",
        rubric=_FAST_BAND_RUBRIC,
        expected_units=_LINES,
        utterances=utterances,
    )


def test_fast_read_matches_fast_band_better_than_slow_read():
    fast = _run_at_rate(4.6)  # inside [4.2, 5.0]
    slow = _run_at_rate(2.2)  # far below the band

    assert fast.status == "scored" and slow.status == "scored"
    # The measured pace flows through to the session profile.
    assert fast.acoustic.speech_rate_sps > slow.acoustic.speech_rate_sps
    # Pace capability separates: the in-band read earns full marks.
    assert fast.capability_scores["pace"] == 1.0
    assert fast.capability_scores["pace"] > slow.capability_scores["pace"]
    # And the headline "did you sound like this speaker" score separates them too.
    assert fast.style_match is not None and slow.style_match is not None
    assert fast.style_match > slow.style_match


def test_slow_read_against_fast_band_flags_too_slow_with_the_real_rate():
    slow = _run_at_rate(2.2)
    pace_cards = [c for c in slow.corrections if c.focus_capability == "pace"]
    assert pace_cards, "a slow read against a fast band must flag pace"
    # The correction cites the measured rate — grounded in audio, not a generic tip.
    assert "2.2 syll/s" in pace_cards[0].explanation
    assert "Lift the energy" in pace_cards[0].explanation

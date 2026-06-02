"""Acoustic analyzers for the persona path: deterministic mock (default) + real.

The mock is the CI/golden default. Its features are a pure function of the
expected line text + seed — never the audio *content* — so two different
recordings of the same line score identically and the suite stays offline and
reproducible. It still honors audio *presence*: an empty recording is the
skipped-line path and yields zeros, so coverage flags a missed line even under the
mock. The real ``LibrosaAcousticAnalyzer`` (``PROVIDER_ACOUSTIC=librosa``) lands in
P2.5 and decodes + measures the actual waveform; it's a demo-machine-only path.
"""

import random

from ..domain.text import estimate_syllables, stable_seed
from ..domain.types import AcousticFeatures
from .base import AcousticAnalyzer


def _has_audio(audio_ref: bytes | str) -> bool:
    """True only for non-empty raw audio bytes (a storage-key string is not audio)."""
    return isinstance(audio_ref, (bytes, bytearray)) and len(audio_ref) > 0


class MockAcousticAnalyzer(AcousticAnalyzer):
    """Deterministic stand-in: plausible features keyed to ``(expected_text, seed)``.

    Ignores the recorded bytes' content (stable golden) but honors their presence:
    an empty/absent recording yields zeroed features — a skipped line reads as
    missed (coverage 0), never fabricated.
    """

    def analyze(
        self, audio_ref: bytes | str, *, expected_text: str, seed: int = 0
    ) -> AcousticFeatures:
        expected = estimate_syllables(expected_text)
        if not _has_audio(audio_ref):
            return AcousticFeatures(expected_syllables=expected)

        # Fixed call order ⇒ a fixed RNG sequence for a given (text, seed).
        rng = random.Random(stable_seed("acoustic", expected_text, seed))
        speech_rate = round(3.3 + rng.uniform(-0.6, 0.6), 3)  # "decent read" ~2.7–3.9 sps
        articulation = round(speech_rate + rng.uniform(0.4, 0.9), 3)
        duration = round(expected / speech_rate, 3) if speech_rate > 0 else 0.0
        pause_total = round(rng.uniform(0.2, 0.8), 3)
        longest_pause = round(min(pause_total, rng.uniform(0.2, 0.5)), 3)
        pause_count = rng.randint(1, 3)
        pitch_range = round(rng.uniform(4.0, 9.0), 3)
        pitch_variation = round(rng.uniform(1.5, 3.5), 3)
        energy_variation = round(rng.uniform(0.25, 0.55), 3)
        voiced_ratio = round(rng.uniform(0.6, 0.85), 3)
        positions = (
            [(round(duration * 0.4, 3), round(duration * 0.4 + longest_pause, 3))]
            if duration > 0
            else []
        )
        return AcousticFeatures(
            duration_s=duration,
            speech_rate_sps=speech_rate,
            articulation_rate_sps=articulation,
            est_syllables=expected,  # mock "hears" the whole line → coverage 1.0
            expected_syllables=expected,
            coverage_ratio=1.0 if expected else 0.0,
            pause_count=pause_count,
            pause_total_s=pause_total,
            longest_pause_s=longest_pause,
            pause_positions=positions,
            pitch_range_semitones=pitch_range,
            pitch_variation=pitch_variation,
            energy_variation=energy_variation,
            voiced_ratio=voiced_ratio,
        )

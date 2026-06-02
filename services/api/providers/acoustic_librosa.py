"""Real acoustic analyzer (librosa) — measures the learner's *actual* waveform.

This is the engine behind the hard rule "judge my speech, not a cleaned-up
transcript":

* **Pace** — syllables/sec from syllable-nuclei peaks on the intensity envelope
  (De Jong & Wempe style), entirely transcript-free.
* **Pauses / breaks** — contiguous low-energy runs in the RMS contour → count,
  durations, positions.
* **Expressiveness** — pitch (F0 via ``librosa.pyin``) range + variation in
  semitones; energy dynamics via the RMS coefficient of variation.
* **Coverage** — detected vs. expected syllables (the script is known), the
  transcript-free proxy for a skipped or truncated line.

Runs only under ``PROVIDER_ACOUSTIC=librosa`` on a demo/dev box with the heavy
deps (librosa, scipy, soundfile, numpy, PyAV — see ``requirements-local.txt``).
CI has none of these, so this module is omitted from POC coverage (``.coveragerc``)
and verified by ``test_acoustic_librosa.py`` wherever librosa is installed; the
registry imports it lazily so its absence never touches the mock path.
"""

import librosa
import numpy as np
from scipy.signal import find_peaks

from ..domain.text import estimate_syllables
from ..domain.types import AcousticFeatures
from .audio_decode import decode_to_pcm
from .base import AcousticAnalyzer

_FRAME = 2048  # pitch (pyin) needs a long window to resolve low F0
_RMS_FRAME = 1024  # energy/silence uses a shorter window so pause edges stay time-accurate
_HOP = 512
_MIN_PAUSE_S = 0.18  # gaps shorter than this are within-speech, not real breaks
_SILENCE_REL_DB = 30.0  # frames > this many dB below the clip's peak count as silence
_ABS_RMS_FLOOR = 1e-3  # absolute energy gate so digital/near silence never reads as voiced
_SYLLABLE_PROMINENCE_DB = 4.0  # a nucleus must stand this far above its surroundings
_MIN_SYLLABLE_GAP_S = 0.12  # people rarely exceed ~8 syllables/sec


def _silent_runs(
    is_silent: "np.ndarray", times: "np.ndarray", duration: float, hop_s: float
) -> list[tuple[float, float]]:
    """Contiguous silent frame-runs (≥ ``_MIN_PAUSE_S``) as (start_s, end_s) spans."""
    runs: list[tuple[float, float]] = []
    n = len(is_silent)
    i = 0
    while i < n:
        if not is_silent[i]:
            i += 1
            continue
        j = i
        while j < n and is_silent[j]:
            j += 1
        start = float(times[i])
        end = min(float(times[j - 1]) + hop_s, duration)  # +1 hop so a run has width
        if end - start >= _MIN_PAUSE_S:
            runs.append((start, end))
        i = j
    return runs


def _pitch_stats(pcm: "np.ndarray", sr: int) -> tuple[float, float]:
    """(range, std) of voiced F0 in semitones — 0 for silence/monotone."""
    f0, _voiced_flag, _voiced_prob = librosa.pyin(
        pcm, fmin=70.0, fmax=400.0, sr=sr, frame_length=_FRAME, hop_length=_HOP
    )
    voiced = f0[~np.isnan(f0)]
    if voiced.size < 2:
        return 0.0, 0.0
    semitones = 12.0 * np.log2(voiced / np.median(voiced))
    spread = float(np.percentile(semitones, 95) - np.percentile(semitones, 5))
    return spread, float(np.std(semitones))


class LibrosaAcousticAnalyzer(AcousticAnalyzer):
    """Decode the recording, then measure delivery acoustics from the raw samples."""

    def analyze(
        self, audio_ref: bytes | str, *, expected_text: str, seed: int = 0
    ) -> AcousticFeatures:
        expected = estimate_syllables(expected_text)
        if not isinstance(audio_ref, (bytes, bytearray)) or not audio_ref:
            return AcousticFeatures(expected_syllables=expected)  # no recording → missed line
        pcm, sr = decode_to_pcm(bytes(audio_ref))
        return self.analyze_pcm(pcm, sr, expected_text=expected_text)

    def analyze_pcm(
        self, pcm: "np.ndarray", sample_rate: int, *, expected_text: str
    ) -> AcousticFeatures:
        """Core measurement on a decoded mono float32 signal (unit-tested directly)."""
        expected = estimate_syllables(expected_text)
        pcm = np.asarray(pcm, dtype=np.float32).reshape(-1)
        if pcm.size == 0 or sample_rate <= 0:
            return AcousticFeatures(expected_syllables=expected)

        duration = float(pcm.size / sample_rate)
        rms = librosa.feature.rms(y=pcm, frame_length=_RMS_FRAME, hop_length=_HOP)[0]
        times = librosa.frames_to_time(np.arange(len(rms)), sr=sample_rate, hop_length=_HOP)
        hop_s = _HOP / float(sample_rate)
        db = librosa.amplitude_to_db(rms, ref=np.max)  # 0 dB at the peak, negative below
        voiced = (db > -_SILENCE_REL_DB) & (rms > _ABS_RMS_FLOOR)

        pauses = _silent_runs(~voiced, times, duration, hop_s)
        pause_total = float(sum(end - start for start, end in pauses))
        longest = max((end - start for start, end in pauses), default=0.0)
        voiced_ratio = float(np.mean(voiced)) if voiced.size else 0.0
        speech_time = max(duration - pause_total, 1e-6)

        min_dist = max(1, int(round(_MIN_SYLLABLE_GAP_S / hop_s)))
        peaks, _props = find_peaks(
            db, height=-_SILENCE_REL_DB, distance=min_dist, prominence=_SYLLABLE_PROMINENCE_DB
        )
        est_syllables = int(np.count_nonzero(voiced[peaks])) if peaks.size else 0

        pitch_range, pitch_variation = _pitch_stats(pcm, sample_rate)
        energy_cv = float(np.std(rms) / (np.mean(rms) + 1e-9)) if rms.size else 0.0
        coverage = (est_syllables / expected) if expected > 0 else 0.0

        return AcousticFeatures(
            duration_s=round(duration, 3),
            speech_rate_sps=round(est_syllables / duration if duration > 0 else 0.0, 3),
            articulation_rate_sps=round(est_syllables / speech_time, 3),
            est_syllables=est_syllables,
            expected_syllables=expected,
            coverage_ratio=round(float(coverage), 3),
            pause_count=len(pauses),
            pause_total_s=round(pause_total, 3),
            longest_pause_s=round(float(longest), 3),
            pause_positions=[(round(s, 3), round(e, 3)) for s, e in pauses],
            pitch_range_semitones=round(pitch_range, 3),
            pitch_variation=round(pitch_variation, 3),
            energy_variation=round(energy_cv, 3),
            voiced_ratio=round(voiced_ratio, 3),
        )

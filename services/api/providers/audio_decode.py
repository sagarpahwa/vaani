"""Decode recorded audio bytes → mono 16 kHz float32 PCM via PyAV.

The persona acoustic path measures pace, pauses, and pitch from the *raw
waveform*, so it needs the learner's actual samples — not a transcript. Browsers
record WebM/Opus and native clients record m4a/AAC; PyAV (already pulled in by
faster-whisper, see ``requirements-local.txt``) demuxes and decodes both, and an
``AudioResampler`` converts whatever came in to the single canonical format the
analyzer expects: **mono, 16 kHz, float32 in [-1, 1]**.

PyAV and numpy are demo-machine-only dependencies (the deterministic mock acoustic
provider needs neither), so this module is imported lazily by the real
``LibrosaAcousticAnalyzer`` and never by the mock/CI path. CI has neither dep, so
this file is omitted from POC coverage (see ``.coveragerc``); its behavior is
covered by ``test_audio_decode.py`` on any box where PyAV is installed.
"""

from io import BytesIO

import av
import numpy as np
from av.audio.resampler import AudioResampler

TARGET_SAMPLE_RATE = 16000


def decode_to_pcm(data: bytes, target_sr: int = TARGET_SAMPLE_RATE) -> tuple[np.ndarray, int]:
    """``webm/opus | m4a | wav`` bytes → ``(mono float32 PCM in [-1, 1], sample_rate)``.

    Empty or non-bytes input yields an empty array (the no-audio path), mirroring
    the STT empty-input guard so an unrecorded line is treated as silence rather
    than fabricated audio.
    """
    if not isinstance(data, (bytes, bytearray)) or not data:
        return np.zeros(0, dtype=np.float32), target_sr

    resampler = AudioResampler(format="flt", layout="mono", rate=target_sr)
    chunks: list[np.ndarray] = []
    with av.open(BytesIO(bytes(data))) as container:
        for frame in container.decode(audio=0):
            for resampled in resampler.resample(frame):
                chunks.append(resampled.to_ndarray().reshape(-1))
        # Flush the resampler's internal buffer (tail samples held back for
        # filtering); without this the final ~milliseconds would be dropped.
        for resampled in resampler.resample(None):
            chunks.append(resampled.to_ndarray().reshape(-1))

    if not chunks:
        return np.zeros(0, dtype=np.float32), target_sr
    return np.concatenate(chunks).astype(np.float32, copy=False), target_sr

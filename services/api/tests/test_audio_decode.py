"""Tests for the PyAV audio-decode util (real-provider path).

The decode util is a demo-machine-only dependency (PyAV + numpy live in
``requirements-local.txt``), so this whole module skips when PyAV is absent —
keeping CI lean and offline, the same stance ``test_whisper_stt.py`` takes toward
the model. Where PyAV *is* installed (the demo / dev box), these exercise the real
demux → decode → resample → mono-float32 pipeline end to end.

Fixtures are synthesized with the stdlib ``wave`` module (not PyAV's encoder), so
the test depends only on PyAV's ability to *decode* PCM-WAV — which every ffmpeg
build supports — not on which optional codecs happen to be bundled.
"""

import io
import math
import struct
import wave

import pytest

pytest.importorskip("av")
np = pytest.importorskip("numpy")

from services.api.providers.audio_decode import decode_to_pcm  # noqa: E402


def _wav_bytes(freq: float = 220.0, secs: float = 0.5, sr: int = 44100, channels: int = 1) -> bytes:
    """A short 16-bit PCM-WAV sine tone at an off-target rate (forces a resample)."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)  # 16-bit
        w.setframerate(sr)
        frames = bytearray()
        for n in range(int(secs * sr)):
            val = int(0.5 * 32767 * math.sin(2 * math.pi * freq * n / sr))
            for _ in range(channels):
                frames += struct.pack("<h", val)
        w.writeframes(bytes(frames))
    return buf.getvalue()


def test_decodes_to_nonempty_mono_16k_float32():
    pcm, sr = decode_to_pcm(_wav_bytes(secs=0.5, sr=44100))
    assert sr == 16000
    assert pcm.dtype == np.float32
    assert pcm.ndim == 1
    assert pcm.size > 0
    # ~0.5 s at 16 kHz ≈ 8000 samples; allow generous slack for resampler edges.
    assert 6000 <= pcm.size <= 9000
    # A 0.5-amplitude tone stays well inside [-1, 1].
    assert float(np.max(np.abs(pcm))) <= 1.0
    assert float(np.max(np.abs(pcm))) > 0.1  # genuinely decoded signal, not silence


def test_stereo_input_collapses_to_mono():
    pcm, sr = decode_to_pcm(_wav_bytes(secs=0.3, sr=44100, channels=2))
    assert sr == 16000
    assert pcm.ndim == 1
    assert pcm.size > 0


def test_resamples_from_native_16k_unchanged_rate():
    # Already at the target rate: still decodes to a non-empty mono float stream.
    pcm, sr = decode_to_pcm(_wav_bytes(secs=0.25, sr=16000))
    assert sr == 16000
    assert pcm.size > 0


def test_empty_bytes_yield_empty_pcm():
    pcm, sr = decode_to_pcm(b"")
    assert sr == 16000
    assert pcm.size == 0
    assert pcm.dtype == np.float32


def test_non_bytes_input_yields_empty_pcm():
    # A storage-key string (not audio bytes) is the no-real-audio path.
    pcm, sr = decode_to_pcm("sessions/s1/utterances/0.wav")  # type: ignore[arg-type]
    assert pcm.size == 0
    assert sr == 16000

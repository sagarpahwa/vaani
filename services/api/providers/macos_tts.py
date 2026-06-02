"""Real text-to-speech via the macOS `say` command.

A demo-machine provider (darwin only): `say` writes a WAVE file directly with an
explicit little-endian 16-bit PCM data format, so the "ideal" re-delivery clip is
real human-sounding speech a browser can play — no sine-wave beep, no extra codec
or conversion step. Selected via `PROVIDER_TTS=macos`; off macOS, use the mock.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

from .base import TTSProvider


class MacSayTTS(TTSProvider):
    """Synthesizes speech with `say -o out.wav --data-format=LEI16@<sr> --file-format=WAVE`.

    Invoked as an argv list with a `--` terminator, so script/user text can never
    be interpreted as shell or option input. The system default voice is used
    unless a voice/rate is configured.
    """

    def __init__(self, voice: str | None = None, rate: int | None = None, sample_rate: int = 22050):
        self._voice = voice
        self._rate = rate
        self._sample_rate = sample_rate

    def synthesize(self, text: str) -> bytes:
        spoken = (text or "").strip() or "."  # `say` rejects empty input
        if shutil.which("say") is None:
            raise RuntimeError(
                "macOS `say` is unavailable on this host; set PROVIDER_TTS=mock instead."
            )
        with tempfile.TemporaryDirectory(prefix="vaani-tts-") as tmp:
            out = Path(tmp) / "ideal.wav"
            cmd = [
                "say",
                "-o",
                str(out),
                f"--data-format=LEI16@{self._sample_rate}",
                "--file-format=WAVE",
            ]
            if self._voice:
                cmd += ["-v", self._voice]
            if self._rate:
                cmd += ["-r", str(self._rate)]
            cmd += ["--", spoken]
            subprocess.run(cmd, check=True, capture_output=True)
            return out.read_bytes()

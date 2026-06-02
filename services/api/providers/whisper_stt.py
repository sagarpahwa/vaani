"""Real speech-to-text via faster-whisper (local CTranslate2 Whisper).

Transcribes the *actual* recorded audio — web `webm/opus` or native `m4a`, decoded
by PyAV — into a timestamped transcript, so the aligner reports the learner's real
mistakes instead of a script-derived approximation. The model loads lazily on first
use and is cached on the instance. CPU + int8 by default: fast enough for short
coaching clips, with no GPU and no cloud credentials. Selected via
`PROVIDER_STT=whisper`; the deterministic mock remains the default elsewhere.

faster-whisper is an optional, demo-machine dependency (see
`services/api/requirements-local.txt`); it is imported lazily so the package's
absence never breaks the mock stack, CI, or the golden regression suite.
"""

from io import BytesIO

from ..domain.text import tokenize
from ..domain.types import Transcript, Word
from .base import STTProvider

# Anti-hallucination guards. Whisper emits confident, coherent sentences on
# silence or noise (its classic failure mode); these thresholds let a quiet or
# empty mic clip resolve to an *empty* transcript ("we didn't catch that")
# instead of fabricated words the aligner would otherwise score as real
# mistakes. A segment is rejected if the model thinks it's probably non-speech
# OR it decoded with very low confidence.
_NO_SPEECH_PROB_MAX = 0.6  # above this, the segment is more likely silence than speech
_AVG_LOGPROB_MIN = -1.0  # below this, the decode is too unsure to trust


class WhisperSTT(STTProvider):
    """Speech-to-text over real audio bytes → a clean, tokenized `Transcript`."""

    def __init__(
        self,
        model_size: str = "base.en",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str = "en",
    ):
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._language = language
        self._model = None

    def _ensure_model(self):
        if self._model is None:
            # On a corporate network the Hugging Face download can fail SSL
            # verification (a self-signed root CA that certifi doesn't carry but
            # the OS keychain does). truststore routes Python's SSL through the
            # system trust store so the one-time model fetch succeeds. It's an
            # optional demo-machine dep — absent in CI, where this branch never
            # runs — so a missing import is a deliberate no-op.
            try:
                import truststore

                truststore.inject_into_ssl()
            except ImportError:
                pass

            from faster_whisper import WhisperModel  # lazy: optional dependency

            self._model = WhisperModel(
                self._model_size, device=self._device, compute_type=self._compute_type
            )
        return self._model

    def warmup(self) -> None:
        """Load (and download, first time) the model now, off the request path."""
        self._ensure_model()

    def transcribe(self, audio_ref: bytes | str, *, expected_text: str, seed: int) -> Transcript:
        # Only real audio bytes are transcribable. A storage-key string or an empty
        # payload (the no-mic skip path) yields an empty transcript — i.e. "nothing
        # was said" — which the aligner correctly scores as every word missed.
        if not isinstance(audio_ref, (bytes, bytearray)) or not audio_ref:
            return Transcript(text="", words=[], duration_seconds=0.0)

        model = self._ensure_model()
        segments, info = model.transcribe(
            BytesIO(bytes(audio_ref)),
            language=self._language,
            word_timestamps=True,
            vad_filter=True,
            condition_on_previous_text=False,  # don't let prior text seed a hallucination run
            no_speech_threshold=_NO_SPEECH_PROB_MAX,
            log_prob_threshold=_AVG_LOGPROB_MIN,
        )

        words: list[Word] = []
        for seg in segments:
            if self._is_hallucinated(seg):
                continue  # probable silence/noise — don't fabricate words for it
            for w in seg.words or []:
                words.extend(self._to_words(w))

        if words:
            duration = words[-1].end
        else:
            duration = round(float(getattr(info, "duration", 0.0) or 0.0), 3)
        text = " ".join(w.word for w in words)
        return Transcript(text=text, words=words, duration_seconds=duration)

    @staticmethod
    def _is_hallucinated(seg) -> bool:
        """True if Whisper likely invented this segment over silence/noise.

        faster-whisper only suppresses a segment when no_speech_prob is high
        *and* avg_logprob is low; applied here as an OR it also catches the
        common case of a confident-looking hallucination over near-silence.
        """
        no_speech = float(getattr(seg, "no_speech_prob", 0.0) or 0.0)
        avg_logprob = float(getattr(seg, "avg_logprob", 0.0) or 0.0)
        return no_speech > _NO_SPEECH_PROB_MAX or avg_logprob < _AVG_LOGPROB_MIN

    @staticmethod
    def _to_words(w) -> list[Word]:
        """Whisper word → one or more clean, lowercase, punctuation-stripped tokens.

        Whisper emits a word with surrounding punctuation/spacing (e.g. ``" There,"``);
        the aligner only strips apostrophes, so each recognized chunk is re-tokenized
        the same way expected text is, keeping the two comparable. A chunk that splits
        into several tokens has its time range spread evenly across them.
        """
        start = round(float(w.start), 3)
        end = round(float(w.end), 3)
        conf = round(float(w.probability), 3)
        toks = tokenize(w.word)
        if not toks:
            return []
        if len(toks) == 1:
            return [Word(word=toks[0], start=start, end=end, confidence=conf)]
        span = max(end - start, 0.0) / len(toks)
        out: list[Word] = []
        for k, tok in enumerate(toks):
            out.append(
                Word(
                    word=tok,
                    start=round(start + k * span, 3),
                    end=round(start + (k + 1) * span, 3),
                    confidence=conf,
                )
            )
        return out

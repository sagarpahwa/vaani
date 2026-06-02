"""Tests for WhisperSTT's pure logic — no model load (faster-whisper not in CI).

Only the parts that don't touch the model are exercised: the empty-input guard,
the anti-hallucination segment filter, and word tokenization. Model loading and
real decoding are demo-machine-only (requirements-local.txt) and covered by
manual verification.
"""

from types import SimpleNamespace

from services.api.providers.whisper_stt import WhisperSTT


def test_non_bytes_ref_yields_empty_transcript():
    # A storage-key string (not audio bytes) is the no-real-audio path.
    t = WhisperSTT().transcribe("sessions/s1/utterances/0.wav", expected_text="hello", seed=1)
    assert t.text == ""
    assert t.words == []
    assert t.duration_seconds == 0.0


def test_empty_bytes_yields_empty_transcript():
    assert WhisperSTT().transcribe(b"", expected_text="hello", seed=1).words == []


def _seg(no_speech, avg_logprob):
    return SimpleNamespace(no_speech_prob=no_speech, avg_logprob=avg_logprob)


def test_is_hallucinated_rejects_probable_silence():
    # High no-speech probability → reject even with an okay logprob.
    assert WhisperSTT._is_hallucinated(_seg(0.95, -0.3)) is True


def test_is_hallucinated_rejects_low_confidence():
    # Very low average logprob → reject even if no_speech_prob looks fine.
    assert WhisperSTT._is_hallucinated(_seg(0.1, -2.0)) is True


def test_is_hallucinated_keeps_confident_speech():
    assert WhisperSTT._is_hallucinated(_seg(0.1, -0.3)) is False


def test_is_hallucinated_handles_missing_fields():
    # A segment object without the probability fields must not crash.
    assert WhisperSTT._is_hallucinated(SimpleNamespace()) is False


def test_to_words_tokenizes_and_strips_punctuation():
    w = SimpleNamespace(word=" There,", start=1.0, end=1.5, probability=0.9)
    out = WhisperSTT._to_words(w)
    assert [x.word for x in out] == ["there"]
    assert out[0].start == 1.0 and out[0].end == 1.5
    assert out[0].confidence == 0.9


def test_to_words_drops_punctuation_only_chunks():
    chunk = SimpleNamespace(word="...", start=0.0, end=0.2, probability=0.5)
    assert WhisperSTT._to_words(chunk) == []


def test_to_words_spreads_time_across_multiple_tokens():
    # A chunk that tokenizes into several words splits its time range evenly.
    w = SimpleNamespace(word="rock-n-roll", start=0.0, end=3.0, probability=0.8)
    out = WhisperSTT._to_words(w)
    assert [x.word for x in out] == ["rock", "n", "roll"]
    assert out[0].start == 0.0
    assert out[-1].end == 3.0
    for prev, cur in zip(out, out[1:]):
        assert cur.start >= prev.start

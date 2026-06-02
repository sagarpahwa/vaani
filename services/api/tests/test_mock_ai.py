"""Tests for the deterministic mock AI: STT, TTS, feedback generation."""

import wave
from io import BytesIO

from services.api.domain.goal_signature import GoalSignature
from services.api.domain.types import Transcript, UtteranceAnalysis, Word
from services.api.providers.analysis import (
    DeliveryFeatureExtractor,
    RubricScorer,
    SequenceAligner,
)
from services.api.providers.base import FILLER_WORDS
from services.api.providers.mock_ai import MockFeedbackGenerator, MockSTT, MockTTS


def test_stt_is_deterministic_for_same_seed():
    stt = MockSTT()
    a = stt.transcribe(b"", expected_text="hello there friends", seed=42)
    b = stt.transcribe(b"", expected_text="hello there friends", seed=42)
    assert a.text == b.text
    assert [w.word for w in a.words] == [w.word for w in b.words]


def test_stt_empty_text_yields_empty_transcript():
    t = MockSTT().transcribe(b"", expected_text="", seed=1)
    assert t.words == []
    assert t.duration_seconds == 0.0


def test_stt_timestamps_are_monotonic():
    t = MockSTT().transcribe(
        b"", expected_text="the quick brown fox jumps over the lazy dog today", seed=7
    )
    for prev, cur in zip(t.words, t.words[1:]):
        assert cur.start >= prev.end - 1e-6


def test_stt_long_script_injects_a_filler():
    t = MockSTT().transcribe(
        b"",
        expected_text="welcome everyone to the launch of our brand new flagship product today",
        seed=3,
    )
    assert any(w.word in FILLER_WORDS for w in t.words)


def test_tts_produces_decodable_wav():
    data = MockTTS().synthesize("hello world this is a test")
    assert data[:4] == b"RIFF"
    with wave.open(BytesIO(data), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert wav.getnframes() > 0


def test_tts_deterministic():
    assert MockTTS().synthesize("same text") == MockTTS().synthesize("same text")


def _analysis(line_index, expected, spoken_words):
    transcript = Transcript(
        text=" ".join(w for w, _, _ in spoken_words),
        words=[Word(word=w, start=s, end=e, confidence=0.9) for w, s, e in spoken_words],
        duration_seconds=(spoken_words[-1][2] if spoken_words else 0.0),
    )
    return UtteranceAnalysis(
        line_index=line_index,
        expected_text=expected,
        transcript=transcript,
        alignment=SequenceAligner().align(expected.split(), [w for w, _, _ in spoken_words]),
        audio_key=f"sessions/s1/utterances/{line_index}.wav",
    )


def test_feedback_generates_improvements_for_weak_delivery():
    analyses = [
        _analysis(
            0,
            "we will win this quarter together",
            [("um", 0.0, 0.6), ("we", 0.7, 1.5), ("will", 2.8, 3.6), ("win", 3.7, 4.9)],
        )
    ]
    feats = DeliveryFeatureExtractor().extract(analyses)
    scores = RubricScorer().score(feats, {c: 1.0 for c in scores_caps()})
    fb, corrections = MockFeedbackGenerator().generate(
        features=feats, scores=scores, analyses=analyses, goal=GoalSignature.from_dict({})
    )
    assert fb.summary
    assert fb.read_aloud_text
    assert len(fb.improvements) >= 1
    assert all(i.severity in ("low", "medium", "high") for i in fb.improvements)


def test_feedback_corrections_carry_audio_keys():
    analyses = [
        _analysis(
            0,
            "this is the original expected line",
            [("this", 0.0, 0.4), ("is", 0.5, 0.7), ("wrong", 0.8, 1.2)],
        )
    ]
    feats = DeliveryFeatureExtractor().extract(analyses)
    scores = RubricScorer().score(feats, {c: 1.0 for c in scores_caps()})
    _, corrections = MockFeedbackGenerator().generate(
        features=feats, scores=scores, analyses=analyses, goal=GoalSignature.from_dict({})
    )
    assert corrections
    assert corrections[0].corrected_text == "this is the original expected line"
    assert corrections[0].user_audio_key == "sessions/s1/utterances/0.wav"


def test_feedback_ignores_skipped_lines():
    """A line with no recorded audio (empty transcript) is never coached as a mistake."""
    skipped_expected = "we built pulse so those two hours come back to you"
    analyses = [
        _analysis(
            0,
            "this is the original expected line",
            [("this", 0.0, 0.4), ("is", 0.5, 0.7), ("wrong", 0.8, 1.2)],
        ),
        _analysis(1, skipped_expected, []),  # never recorded → empty transcript
    ]
    feats = DeliveryFeatureExtractor().extract(analyses)
    scores = RubricScorer().score(feats, {c: 1.0 for c in scores_caps()})
    fb, corrections = MockFeedbackGenerator().generate(
        features=feats, scores=scores, analyses=analyses, goal=GoalSignature.from_dict({})
    )
    # No correction card for the skipped line, and none echoes its script text back.
    assert all(c.line_index != 1 for c in corrections)
    assert all(c.original_text != skipped_expected for c in corrections)
    # No "Line 2: you skipped …" concrete callout for the unrecorded line.
    assert all("Line 2" not in imp.message for imp in fb.improvements)


def scores_caps():
    from services.api.domain.goal_signature import CANONICAL_CAPABILITIES

    return CANONICAL_CAPABILITIES

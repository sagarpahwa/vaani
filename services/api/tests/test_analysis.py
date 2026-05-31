"""Tests for the deterministic analysis providers."""

from services.api.domain.goal_signature import CANONICAL_CAPABILITIES
from services.api.domain.types import Transcript, UtteranceAnalysis, Word
from services.api.providers.analysis import (
    DeliveryFeatureExtractor,
    RubricScorer,
    SequenceAligner,
)


def _words(pairs):
    """Build Word list from (text, start, end) triples at 0.95 confidence."""
    return [Word(word=w, start=s, end=e, confidence=0.95) for w, s, e in pairs]


def test_aligner_identical_is_all_match():
    ops = SequenceAligner().align(["hello", "world"], ["hello", "world"])
    assert [o.op for o in ops] == ["match", "match"]


def test_aligner_detects_sub_insert_delete():
    ops = SequenceAligner().align(["the", "quick", "fox"], ["the", "slow", "brown", "fox"])
    kinds = [o.op for o in ops]
    assert "sub" in kinds or "insert" in kinds
    # Reference fully consumed.
    assert sum(1 for o in ops if o.op in ("match", "sub", "delete")) == 3


def test_aligner_empty_inputs():
    assert SequenceAligner().align([], []) == []


def test_feature_extractor_counts_fillers_and_wpm():
    transcript = Transcript(
        text="um hello there world",
        words=_words(
            [("um", 0.0, 0.3), ("hello", 0.4, 0.8), ("there", 0.9, 1.3), ("world", 1.4, 1.8)]
        ),
        duration_seconds=2.0,
    )
    analysis = UtteranceAnalysis(
        line_index=0,
        expected_text="hello there world",
        transcript=transcript,
        alignment=SequenceAligner().align(
            ["hello", "there", "world"], ["um", "hello", "there", "world"]
        ),
    )
    feats = DeliveryFeatureExtractor().extract([analysis])
    assert feats.filler_count == 1
    assert feats.word_count == 4
    assert feats.words_per_minute > 0


def test_feature_extractor_empty():
    feats = DeliveryFeatureExtractor().extract([])
    assert feats.word_count == 0
    assert feats.words_per_minute == 0.0
    assert feats.accuracy == 0.0


def test_scorer_bounds_and_keys():
    feats = DeliveryFeatureExtractor().extract(
        [
            UtteranceAnalysis(
                line_index=0,
                expected_text="hello world",
                transcript=Transcript(
                    text="hello world",
                    words=_words([("hello", 0.0, 0.4), ("world", 0.5, 0.9)]),
                    duration_seconds=1.0,
                ),
                alignment=SequenceAligner().align(["hello", "world"], ["hello", "world"]),
            )
        ]
    )
    weights = {c: 1.0 for c in CANONICAL_CAPABILITIES}
    result = RubricScorer().score(feats, weights)
    assert set(result.capabilities) == set(CANONICAL_CAPABILITIES)
    assert 0.0 <= result.overall_score <= 1.0
    assert all(0.0 <= v <= 1.0 for v in result.capabilities.values())


def test_scorer_perfect_beats_filler_heavy():
    aligner = SequenceAligner()
    clean = DeliveryFeatureExtractor().extract(
        [
            UtteranceAnalysis(
                line_index=0,
                expected_text="we deliver clear value to every customer",
                transcript=Transcript(
                    text="we deliver clear value to every customer",
                    words=_words(
                        [
                            ("we", 0.0, 0.3),
                            ("deliver", 0.4, 0.8),
                            ("clear", 0.9, 1.2),
                            ("value", 1.3, 1.6),
                            ("to", 1.7, 1.9),
                            ("every", 2.0, 2.3),
                            ("customer", 2.4, 2.9),
                        ]
                    ),
                    duration_seconds=3.0,
                ),
                alignment=aligner.align(
                    "we deliver clear value to every customer".split(),
                    "we deliver clear value to every customer".split(),
                ),
            )
        ]
    )
    weights = {c: 1.0 for c in CANONICAL_CAPABILITIES}
    assert RubricScorer().score(clean, weights).overall_score > 0.5

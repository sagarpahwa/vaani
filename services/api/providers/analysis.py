"""Deterministic analysis providers: alignment, feature extraction, scoring.

These are pure math (no AI, no network). The aligner is classic Levenshtein DP;
the scorer maps observed delivery features onto the six canonical capabilities
with simple, explainable curves. Same input → same output, always.
"""

from ..domain.goal_signature import CANONICAL_CAPABILITIES
from ..domain.text import normalize, tokenize
from ..domain.types import (
    AlignOp,
    DeliveryFeatures,
    ScoreResult,
    UtteranceAnalysis,
)
from .base import FILLER_WORDS, Aligner, FeatureExtractor, Scorer

# A silent gap longer than this (seconds) between consecutive words counts as a
# disruptive pause. Short gaps are natural phrasing.
LONG_PAUSE_SECONDS = 1.0
# Ideal speaking rate band (words per minute). Scores peak inside this band.
TARGET_WPM_LOW = 110.0
TARGET_WPM_HIGH = 160.0


class SequenceAligner(Aligner):
    """Word-level alignment via Levenshtein edit distance with backtrace."""

    def align(self, expected: list[str], hypothesis: list[str]) -> list[AlignOp]:
        ref = [normalize(w) for w in expected]
        hyp = [normalize(w) for w in hypothesis]
        n, m = len(ref), len(hyp)
        # dp[i][j] = min edits to turn ref[:i] into hyp[:j].
        dp = [[0] * (m + 1) for _ in range(n + 1)]
        for i in range(1, n + 1):
            dp[i][0] = i
        for j in range(1, m + 1):
            dp[0][j] = j
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                cost = 0 if ref[i - 1] == hyp[j - 1] else 1
                dp[i][j] = min(
                    dp[i - 1][j] + 1,  # delete from ref
                    dp[i][j - 1] + 1,  # insert from hyp
                    dp[i - 1][j - 1] + cost,  # match / substitute
                )
        return self._backtrace(dp, ref, hyp, expected, hypothesis)

    @staticmethod
    def _backtrace(dp, ref, hyp, expected, hypothesis) -> list[AlignOp]:
        ops: list[AlignOp] = []
        i, j = len(ref), len(hyp)
        while i > 0 or j > 0:
            if i > 0 and j > 0:
                cost = 0 if ref[i - 1] == hyp[j - 1] else 1
                if dp[i][j] == dp[i - 1][j - 1] + cost:
                    op = "match" if cost == 0 else "sub"
                    ops.append(AlignOp(op=op, ref=expected[i - 1], hyp=hypothesis[j - 1]))
                    i, j = i - 1, j - 1
                    continue
            if i > 0 and dp[i][j] == dp[i - 1][j] + 1:
                ops.append(AlignOp(op="delete", ref=expected[i - 1], hyp=None))
                i -= 1
            else:
                ops.append(AlignOp(op="insert", ref=None, hyp=hypothesis[j - 1]))
                j -= 1
        ops.reverse()
        return ops


class DeliveryFeatureExtractor(FeatureExtractor):
    """Aggregates per-utterance analyses into one feature vector."""

    def extract(self, analyses: list[UtteranceAnalysis]) -> DeliveryFeatures:
        word_count = 0
        expected_word_count = 0
        duration = 0.0
        filler_count = 0
        matches = 0
        ref_total = 0
        stumble_count = 0
        long_pause_count = 0

        for a in analyses:
            words = a.transcript.words
            word_count += len(words)
            expected_word_count += len(tokenize(a.expected_text))
            duration += max(a.transcript.duration_seconds, 0.0)
            filler_count += sum(1 for w in words if normalize(w.word) in FILLER_WORDS)
            # Alignment-derived accuracy + stumbles.
            for op in a.alignment:
                if op.op in ("match", "sub", "delete"):
                    ref_total += 1
                if op.op == "match":
                    matches += 1
                if op.op in ("sub", "insert"):
                    stumble_count += 1
            # Long silent gaps between consecutive recognized words.
            for prev, cur in zip(words, words[1:]):
                if cur.start - prev.end > LONG_PAUSE_SECONDS:
                    long_pause_count += 1

        wpm = (word_count / duration * 60.0) if duration > 0 else 0.0
        accuracy = (matches / ref_total) if ref_total > 0 else 0.0
        filler_rate = (filler_count / word_count) if word_count > 0 else 0.0

        return DeliveryFeatures(
            word_count=word_count,
            expected_word_count=expected_word_count,
            duration_seconds=round(duration, 3),
            words_per_minute=round(wpm, 2),
            filler_count=filler_count,
            filler_rate=round(filler_rate, 4),
            accuracy=round(accuracy, 4),
            stumble_count=stumble_count,
            long_pause_count=long_pause_count,
        )


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _pace_score(wpm: float) -> float:
    """1.0 inside the target band, decaying linearly outside it."""
    if wpm <= 0:
        return 0.0
    if TARGET_WPM_LOW <= wpm <= TARGET_WPM_HIGH:
        return 1.0
    if wpm < TARGET_WPM_LOW:
        return _clamp01(1.0 - (TARGET_WPM_LOW - wpm) / TARGET_WPM_LOW)
    return _clamp01(1.0 - (wpm - TARGET_WPM_HIGH) / TARGET_WPM_HIGH)


class RubricScorer(Scorer):
    """Maps features to the six canonical capabilities, then a weighted overall.

    Each capability is a transparent function of one or two features so feedback
    can explain *why* a score moved. The overall is the weight-adjusted mean,
    where weights come from the learner's Goal Signature.
    """

    def score(self, features: DeliveryFeatures, weights: dict[str, float]) -> ScoreResult:
        f = features
        caps = {
            "clarity": _clamp01(0.5 + 0.5 * f.accuracy - 0.5 * f.filler_rate),
            "pace": _pace_score(f.words_per_minute),
            "fluency": _clamp01(1.0 - f.filler_rate - 0.1 * f.long_pause_count),
            "confidence": _clamp01(0.45 + 0.6 * f.accuracy - 0.08 * f.stumble_count),
            "engagement": _clamp01(
                0.5 + 0.5 * _pace_score(f.words_per_minute) - 0.5 * f.filler_rate
            ),
            "conciseness": self._conciseness(f),
        }
        caps = {k: round(v, 4) for k, v in caps.items()}

        weighted_sum = sum(caps[c] * weights.get(c, 1.0) for c in CANONICAL_CAPABILITIES)
        weight_total = sum(weights.get(c, 1.0) for c in CANONICAL_CAPABILITIES)
        overall = round(weighted_sum / weight_total, 4) if weight_total > 0 else 0.0

        return ScoreResult(overall_score=overall, capabilities=caps, weights=dict(weights))

    @staticmethod
    def _conciseness(f: DeliveryFeatures) -> float:
        """Penalize speaking far more words than the script expected."""
        if f.expected_word_count <= 0:
            return _clamp01(1.0 - f.filler_rate)
        ratio = f.word_count / f.expected_word_count
        # 1.0 when at/under expected length; decays as you run long.
        overrun = max(0.0, ratio - 1.0)
        return _clamp01(1.0 - 0.8 * overrun - 0.5 * f.filler_rate)

"""Deterministic mock AI: STT, TTS, and feedback generation.

No cloud, no randomness that varies across runs. Every output is a pure
function of the input plus an explicit integer seed, so a given utterance always
produces the same transcript, the same fillers, and the same feedback. This is
what makes the whole pipeline unit-testable and demo-reproducible.
"""

import math
import random
import struct
import wave
from io import BytesIO

from ..domain.goal_signature import GoalSignature
from ..domain.text import normalize, tokenize
from ..domain.types import (
    CorrectionDraft,
    DeliveryFeatures,
    FeedbackResult,
    Improvement,
    ScoreResult,
    Transcript,
    UtteranceAnalysis,
    Word,
)
from .base import FILLER_WORDS, FeedbackGenerator, STTProvider, TTSProvider

# Per-word base duration (seconds) before jitter. ~0.34s ≈ 145 wpm baseline.
_BASE_WORD_SECONDS = 0.34
# Fillers the mock injects, in priority order.
_INJECTABLE_FILLERS = ["um", "uh", "like"]


class MockSTT(STTProvider):
    """Synthesizes a plausible timestamped transcript from the expected text.

    The seed deterministically decides where fillers are inserted, which words
    are omitted (stumbles), and how pacing jitters — so we can demo realistic
    "imperfect" delivery without any real audio or model.
    """

    def transcribe(self, audio_ref: bytes | str, *, expected_text: str, seed: int) -> Transcript:
        rng = random.Random(seed)
        expected_tokens = tokenize(expected_text)
        if not expected_tokens:
            return Transcript(text="", words=[], duration_seconds=0.0)

        emitted: list[str] = []
        for idx, tok in enumerate(expected_tokens):
            # Occasionally drop a word (omission/stumble), but never the first.
            if idx > 0 and rng.random() < 0.06:
                continue
            # Occasionally inject a filler before a word.
            if rng.random() < 0.08:
                emitted.append(rng.choice(_INJECTABLE_FILLERS))
            emitted.append(tok)
        # Guarantee at least one filler on longer scripts so demos show fillers.
        if len(expected_tokens) >= 12 and not any(
            normalize(w) in _INJECTABLE_FILLERS for w in emitted
        ):
            emitted.insert(min(2, len(emitted)), rng.choice(_INJECTABLE_FILLERS))

        words: list[Word] = []
        t = round(0.15 + rng.random() * 0.2, 3)  # small lead-in silence
        for tok in emitted:
            dur = _BASE_WORD_SECONDS * (0.8 + rng.random() * 0.6)
            # Occasionally insert a longer pause (hesitation) before a word.
            if rng.random() < 0.05:
                t += 1.1 + rng.random() * 0.5
            start = round(t, 3)
            end = round(t + dur, 3)
            conf = round(0.82 + rng.random() * 0.17, 3)
            words.append(Word(word=tok, start=start, end=end, confidence=conf))
            t = end + round(0.04 + rng.random() * 0.06, 3)

        duration = round(words[-1].end + 0.1, 3) if words else 0.0
        text = " ".join(w.word for w in words)
        return Transcript(text=text, words=words, duration_seconds=duration)


class MockTTS(TTSProvider):
    """Generates a valid mono 16-bit PCM WAV whose tone/length depend on the text.

    Real players can decode it; the duration scales with word count so an "ideal"
    re-delivery clip feels proportional. Deterministic: same text → same bytes.
    """

    SAMPLE_RATE = 16000

    def synthesize(self, text: str) -> bytes:
        tokens = tokenize(text)
        # ~0.3s per word, clamped to a sensible demo range.
        seconds = max(0.4, min(8.0, len(tokens) * 0.3 or 0.4))
        n_samples = int(self.SAMPLE_RATE * seconds)
        # Pitch derived from text length so different clips sound different.
        freq = 180.0 + (len(text) % 7) * 25.0
        amp = 12000

        buf = BytesIO()
        with wave.open(buf, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(self.SAMPLE_RATE)
            frames = bytearray()
            for i in range(n_samples):
                sample = int(amp * math.sin(2 * math.pi * freq * (i / self.SAMPLE_RATE)))
                frames += struct.pack("<h", sample)
            wav.writeframes(bytes(frames))
        return buf.getvalue()


# Capability → human-readable coaching message templates.
_IMPROVEMENT_TEMPLATES = {
    "pace": "Your pace was {detail}. Aim for a steady 110–160 words per minute.",
    "fluency": "You used {n} filler word(s). Pause silently instead of saying 'um' or 'like'.",
    "clarity": "Some words didn't land clearly. Slow down on key phrases and enunciate.",
    "confidence": "A few stumbles broke your flow. Rehearse the opening lines until automatic.",
    "engagement": "Vary your energy and emphasis to keep the audience leaning in.",
    "conciseness": "You ran long versus the script. Tighten to the essential message.",
}

_STRENGTH_TEMPLATES = {
    "pace": "Your pacing sat in the ideal range.",
    "fluency": "Your delivery was smooth with very few fillers.",
    "clarity": "Your words came through clearly and accurately.",
    "confidence": "You sounded confident and in control.",
    "engagement": "Your delivery had good energy.",
    "conciseness": "You stayed tight to the script.",
}

# Severity thresholds on a capability's 0–1 score.
_SEV_HIGH = 0.55
_SEV_MEDIUM = 0.7
_STRENGTH_FLOOR = 0.8

# How many concrete word-level mistakes to call out, and how many errors per line.
_MAX_CONCRETE_LINES = 2
_MAX_ERRORS_PER_LINE = 3
# A line with at least this many word errors is flagged "high" severity.
_CONCRETE_HIGH_ERRORS = 3


def _was_recorded(a: UtteranceAnalysis) -> bool:
    """True only if the learner actually produced audio for this line.

    An empty transcript means the line was skipped (no-mic path) or came back
    silent — *not* a delivery mistake. Such a line must never surface a
    "you said …"/"you skipped …" callout or a correction card, and must never
    echo the expected text back as what was said.
    """
    return bool(a.transcript.words)


class MockFeedbackGenerator(FeedbackGenerator):
    """Turns features + scores + alignment into written feedback and A/B drafts.

    Templated and deterministic. Improvements are ranked worst-capability-first;
    correction drafts target the lines with the most alignment errors so the
    read-aloud "ideal" clip is maximally useful.
    """

    def generate(
        self,
        *,
        features: DeliveryFeatures,
        scores: ScoreResult,
        analyses: list[UtteranceAnalysis],
        goal: GoalSignature,
    ) -> tuple[FeedbackResult, list[CorrectionDraft]]:
        # Lead with concrete, real word-level mistakes pulled straight from the
        # alignment (grounded in what was actually said vs. the script); fall back
        # to the score-derived templates for delivery aspects not about word
        # accuracy. Concrete clarity callouts replace the generic clarity template.
        concrete = self._concrete_mistakes(analyses)
        covered = {imp.capability for imp in concrete}
        scored = [
            imp for imp in self._improvements(features, scores) if imp.capability not in covered
        ]
        improvements = (concrete + scored)[:5]
        strengths = [
            _STRENGTH_TEMPLATES[cap]
            for cap, sc in sorted(scores.capabilities.items(), key=lambda kv: -kv[1])
            if sc >= _STRENGTH_FLOOR
        ][:3]
        if not strengths:
            strengths = ["You completed the full practice — that's the hardest part."]

        summary = self._summary(scores.overall_score, goal)
        read_aloud = self._read_aloud(scores.overall_score, strengths, improvements)
        corrections = self._corrections(analyses, scores)
        return (
            FeedbackResult(
                summary=summary,
                strengths=strengths,
                improvements=improvements,
                read_aloud_text=read_aloud,
            ),
            corrections,
        )

    @staticmethod
    def _concrete_mistakes(analyses: list[UtteranceAnalysis]) -> list[Improvement]:
        """Real word-level errors from the alignment → specific, grounded callouts.

        Reports the actual diffs the learner made — substituted, skipped, or added
        words — for the lines with the most errors, so feedback says *what* went
        wrong instead of a generic "some words didn't land". Inserted fillers are
        excluded here (the fluency score already covers them).
        """
        ranked: list[tuple[int, int, list[tuple[str, str]], list[str], list[str]]] = []
        for a in analyses:
            if not _was_recorded(a):
                continue  # skipped/silent line — not a mistake the learner made
            subs = [(op.ref, op.hyp) for op in a.alignment if op.op == "sub"]
            missed = [op.ref for op in a.alignment if op.op == "delete"]
            added = [
                op.hyp
                for op in a.alignment
                if op.op == "insert" and normalize(op.hyp or "") not in FILLER_WORDS
            ]
            errors = len(subs) + len(missed) + len(added)
            if errors:
                ranked.append((errors, a.line_index, subs, missed, added))
        ranked.sort(key=lambda r: (-r[0], r[1]))  # worst lines first, stable by line

        out: list[Improvement] = []
        for errors, line_index, subs, missed, added in ranked[:_MAX_CONCRETE_LINES]:
            bits: list[str] = []
            if subs:
                bits.append(
                    "; ".join(
                        f'said "{h}" instead of "{r}"' for r, h in subs[:_MAX_ERRORS_PER_LINE]
                    )
                )
            if missed:
                bits.append("skipped " + ", ".join(f'"{w}"' for w in missed[:_MAX_ERRORS_PER_LINE]))
            if added:
                bits.append("added " + ", ".join(f'"{w}"' for w in added[:_MAX_ERRORS_PER_LINE]))
            severity = "high" if errors >= _CONCRETE_HIGH_ERRORS else "medium"
            out.append(
                Improvement(
                    capability="clarity",
                    message=f"Line {line_index + 1}: you " + "; ".join(bits) + ".",
                    severity=severity,
                    line_index=line_index,
                )
            )
        return out

    @staticmethod
    def _improvements(features: DeliveryFeatures, scores: ScoreResult) -> list[Improvement]:
        out: list[Improvement] = []
        for cap, sc in sorted(scores.capabilities.items(), key=lambda kv: kv[1]):
            if sc >= _SEV_MEDIUM:
                continue
            severity = "high" if sc < _SEV_HIGH else "medium"
            template = _IMPROVEMENT_TEMPLATES[cap]
            if cap == "pace":
                wpm = features.words_per_minute
                detail = "a bit fast" if wpm > 160 else "a bit slow" if wpm < 110 else "uneven"
                message = template.format(detail=f"{detail} ({wpm:.0f} wpm)")
            elif cap == "fluency":
                message = template.format(n=features.filler_count)
            else:
                message = template
            out.append(Improvement(capability=cap, message=message, severity=severity))
        return out

    @staticmethod
    def _summary(overall: float, goal: GoalSignature) -> str:
        band = (
            "a strong run"
            if overall >= 0.8
            else "solid progress" if overall >= 0.6 else "a good start"
        )
        occasion = f" for your {goal.occasion}" if goal.occasion else ""
        return (
            f"Overall {overall:.0%} — {band}{occasion}. "
            "Here's what stood out and what to work on next."
        )

    @staticmethod
    def _read_aloud(overall: float, strengths: list[str], improvements: list[Improvement]) -> str:
        parts = [f"You scored {overall:.0%} overall."]
        if strengths:
            parts.append(strengths[0])
        if improvements:
            parts.append("To improve: " + improvements[0].message)
        else:
            parts.append("Keep practicing to lock in this level.")
        return " ".join(parts)

    def _corrections(
        self, analyses: list[UtteranceAnalysis], scores: ScoreResult
    ) -> list[CorrectionDraft]:
        # Worst capability overall drives the coaching focus of each card.
        focus = (
            min(scores.capabilities, key=scores.capabilities.get)
            if scores.capabilities
            else "clarity"
        )
        # Only coach lines that were actually recorded — a skipped/silent line
        # has an empty transcript and must not get a card echoing the script
        # back as what was said.
        ranked = sorted(
            (a for a in analyses if _was_recorded(a)), key=self._error_count, reverse=True
        )
        drafts: list[CorrectionDraft] = []
        for a in ranked[:2]:
            if self._error_count(a) == 0:
                continue
            drafts.append(
                CorrectionDraft(
                    line_index=a.line_index,
                    focus_capability=focus,
                    original_text=a.transcript.text,
                    corrected_text=a.expected_text,
                    explanation=(
                        "Here's the line delivered cleanly — match this phrasing and pacing, "
                        "then re-record."
                    ),
                    user_audio_key=a.audio_key,
                )
            )
        return drafts

    @staticmethod
    def _error_count(a: UtteranceAnalysis) -> int:
        return sum(1 for op in a.alignment if op.op != "match")

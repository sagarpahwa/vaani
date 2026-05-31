"""The coaching pipeline: utterances → analysis → score → feedback → result.

Pure orchestration over the provider interfaces. Given a session's expected
units (script lines, or user-script lines for Mode B) and the recorded
utterances, it produces one `PipelineResult` ready to persist. Deterministic:
identical input yields identical output.
"""

from ..providers.registry import ProviderBundle
from .goal_signature import GoalSignature, capability_weights
from .text import stable_seed
from .types import PipelineResult, UtteranceAnalysis
from .versions import version_stamp


def compute_delta(old: dict[str, float] | None, new: dict[str, float]) -> dict[str, float]:
    """Per-capability (and overall) score change from a previous attempt.

    Keys present in `new` are diffed against `old` (missing → treated as 0). A
    retry surfaces this so the learner sees exactly what improved.
    """
    old = old or {}
    return {k: round(new[k] - old.get(k, 0.0), 4) for k in new}


class CoachingPipeline:
    """Runs the deterministic coaching analysis over recorded utterances."""

    def __init__(self, providers: ProviderBundle):
        self.p = providers

    def analyze_utterances(
        self,
        *,
        session_id: str,
        expected_units: list[str],
        utterances: list[dict],
    ) -> list[UtteranceAnalysis]:
        """Transcribe + align each utterance against its expected text.

        `utterances` items are dicts with at least `line_index`; optional
        `audio_key` (already-stored audio) and `expected_text` override. The seed
        is derived from session + line so re-running is reproducible.
        """
        analyses: list[UtteranceAnalysis] = []
        for u in utterances:
            line_index = u["line_index"]
            expected_text = u.get("expected_text")
            if expected_text is None:
                expected_text = (
                    expected_units[line_index] if 0 <= line_index < len(expected_units) else ""
                )
            audio_key = u.get("audio_key")
            seed = stable_seed(session_id, line_index, expected_text)
            transcript = self.p.stt.transcribe(
                audio_key or b"", expected_text=expected_text, seed=seed
            )
            from .text import tokenize

            alignment = self.p.aligner.align(
                tokenize(expected_text), [w.word for w in transcript.words]
            )
            analyses.append(
                UtteranceAnalysis(
                    line_index=line_index,
                    expected_text=expected_text,
                    transcript=transcript,
                    alignment=alignment,
                    audio_key=audio_key,
                )
            )
        return analyses

    def run(
        self,
        *,
        session_id: str,
        goal: GoalSignature,
        expected_units: list[str],
        utterances: list[dict],
        parent_scores: dict[str, float] | None = None,
    ) -> PipelineResult:
        """Full run: analyze → extract features → score → generate feedback.

        Returns a `failed` result (rather than raising) when there is nothing to
        score, so the caller can persist a terminal status for the session.
        """
        if not utterances:
            return self._empty_result("failed")

        analyses = self.analyze_utterances(
            session_id=session_id, expected_units=expected_units, utterances=utterances
        )
        features = self.p.feature_extractor.extract(analyses)
        weights = capability_weights(goal)
        scores = self.p.scorer.score(features, weights)
        feedback, corrections = self.p.feedback.generate(
            features=features, scores=scores, analyses=analyses, goal=goal
        )

        # Synthesize an "ideal" re-delivery clip for each correction card.
        for c in corrections:
            audio = self.p.tts.synthesize(c.corrected_text)
            key = f"sessions/{session_id}/corrections/{c.line_index}-ideal.wav"
            self.p.store.put(key, audio)
            c.ideal_audio_key = key

        new_scores = {"overall": scores.overall_score, **scores.capabilities}
        delta = compute_delta(parent_scores, new_scores) if parent_scores else None

        return PipelineResult(
            status="scored",
            overall_score=scores.overall_score,
            capability_scores=scores.capabilities,
            features=features,
            feedback=feedback,
            corrections=corrections,
            versions=version_stamp(),
            delta=delta,
            analyses=analyses,
        )

    def retry(
        self,
        *,
        session_id: str,
        goal: GoalSignature,
        expected_units: list[str],
        utterances: list[dict],
        parent_scores: dict[str, float],
    ) -> PipelineResult:
        """A retry run that always computes a delta vs. the parent attempt."""
        return self.run(
            session_id=session_id,
            goal=goal,
            expected_units=expected_units,
            utterances=utterances,
            parent_scores=parent_scores,
        )

    @staticmethod
    def _empty_result(status: str) -> PipelineResult:
        from .types import DeliveryFeatures, FeedbackResult

        empty_features = DeliveryFeatures(
            word_count=0,
            expected_word_count=0,
            duration_seconds=0.0,
            words_per_minute=0.0,
            filler_count=0,
            filler_rate=0.0,
            accuracy=0.0,
            stumble_count=0,
            long_pause_count=0,
        )
        return PipelineResult(
            status=status,
            overall_score=0.0,
            capability_scores={},
            features=empty_features,
            feedback=FeedbackResult(
                summary="No utterances were recorded, so there's nothing to score yet.",
                strengths=[],
                improvements=[],
                read_aloud_text="No audio was captured. Record your lines and try again.",
            ),
            corrections=[],
            versions=version_stamp(),
            delta=None,
            analyses=[],
        )

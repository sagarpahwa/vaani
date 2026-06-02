"""Tests for the end-to-end coaching pipeline orchestration."""

from services.api.domain.goal_signature import GoalSignature
from services.api.domain.pipeline import CoachingPipeline, compute_delta
from services.api.providers.object_store import InMemoryObjectStore
from services.api.providers.registry import build_providers


class _Settings:
    """Minimal stand-in for app settings (all-mock provider stack)."""

    provider_stt = "mock"
    provider_tts = "mock"
    provider_llm = "mock"
    object_store = "memory"
    poc_storage_dir = "./.poc-storage"


def _pipeline():
    providers = build_providers(_Settings(), store=InMemoryObjectStore())
    return CoachingPipeline(providers), providers


def test_run_guided_session_produces_scored_result():
    pipe, providers = _pipeline()
    units = [
        "hello everyone and welcome to the team",
        "today we are launching our new product",
    ]
    utterances = [{"line_index": 0}, {"line_index": 1}]
    result = pipe.run(
        session_id="sess-1",
        goal=GoalSignature.from_dict({"occasion": "team address"}),
        expected_units=units,
        utterances=utterances,
    )
    assert result.status == "scored"
    assert 0.0 <= result.overall_score <= 1.0
    assert set(result.capability_scores)
    # Version fields stamped.
    assert result.versions["rubric_version"]
    assert result.versions["scoring_model_version"]
    # Ideal-audio clips were synthesized and stored for any corrections.
    for c in result.corrections:
        assert c.ideal_audio_key is not None
        assert providers.store.exists(c.ideal_audio_key)


def test_run_is_deterministic():
    pipe, _ = _pipeline()
    units = ["the quarterly numbers came in stronger than we expected"]
    args = dict(
        session_id="sess-det",
        goal=GoalSignature.from_dict({"objective": "briefing"}),
        expected_units=units,
        utterances=[{"line_index": 0}],
    )
    a = pipe.run(**args)
    b = pipe.run(**args)
    assert a.overall_score == b.overall_score
    assert a.capability_scores == b.capability_scores


def test_run_empty_utterances_is_failed():
    pipe, _ = _pipeline()
    result = pipe.run(
        session_id="sess-empty",
        goal=GoalSignature.from_dict({}),
        expected_units=["anything"],
        utterances=[],
    )
    assert result.status == "failed"
    assert result.overall_score == 0.0
    assert result.corrections == []


def test_mode_b_uses_inline_expected_text():
    """Mode B passes the user's own script text per utterance (no script lines)."""
    pipe, _ = _pipeline()
    result = pipe.run(
        session_id="sess-modeb",
        goal=GoalSignature.from_dict({"objective": "user script"}),
        expected_units=[],
        utterances=[
            {"line_index": 0, "expected_text": "my fellow citizens we stand at a turning point"},
            {"line_index": 1, "expected_text": "and together we will choose the harder right"},
        ],
    )
    assert result.status == "scored"
    assert result.features.expected_word_count > 0


def test_retry_computes_delta():
    pipe, _ = _pipeline()
    units = ["we will deliver clear and concise value to our customers"]
    parent = pipe.run(
        session_id="sess-parent",
        goal=GoalSignature.from_dict({}),
        expected_units=units,
        utterances=[{"line_index": 0}],
    )
    parent_scores = {"overall": parent.overall_score, **parent.capability_scores}
    retry = pipe.retry(
        session_id="sess-retry",
        goal=GoalSignature.from_dict({}),
        expected_units=units,
        utterances=[{"line_index": 0}],
        parent_scores=parent_scores,
    )
    assert retry.delta is not None
    assert "overall" in retry.delta


def test_compute_delta_handles_missing_keys():
    delta = compute_delta({"clarity": 0.5}, {"clarity": 0.8, "pace": 0.6})
    assert delta["clarity"] == 0.3
    assert delta["pace"] == 0.6
    assert compute_delta(None, {"clarity": 0.4}) == {"clarity": 0.4}

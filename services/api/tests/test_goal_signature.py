"""Tests for Goal Signature parsing and rubric re-weighting."""

from services.api.domain.goal_signature import (
    CANONICAL_CAPABILITIES,
    GoalSignature,
    capability_weights,
)


def test_from_dict_defaults_and_extra():
    gs = GoalSignature.from_dict({"objective": "Pitch", "team": "growth"})
    assert gs.objective == "Pitch"
    assert gs.language == "en"
    assert gs._extra == {"team": "growth"}


def test_from_dict_none_is_empty():
    gs = GoalSignature.from_dict(None)
    assert gs.objective == ""
    assert gs.to_dict()["language"] == "en"


def test_weights_mean_is_one():
    gs = GoalSignature.from_dict({"occasion": "investor pitch"})
    weights = capability_weights(gs)
    assert set(weights) == set(CANONICAL_CAPABILITIES)
    mean = sum(weights.values()) / len(weights)
    assert abs(mean - 1.0) < 1e-6


def test_pitch_boosts_conciseness_over_neutral():
    pitch = capability_weights(GoalSignature.from_dict({"occasion": "investor pitch"}))
    toast = capability_weights(GoalSignature.from_dict({"occasion": "wedding toast"}))
    assert pitch["conciseness"] > toast["conciseness"]
    assert toast["engagement"] > pitch["engagement"]


def test_empty_goal_is_uniform():
    weights = capability_weights(GoalSignature.from_dict({}))
    assert all(abs(w - 1.0) < 1e-6 for w in weights.values())

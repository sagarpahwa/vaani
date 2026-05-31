"""Pinned version identifiers for the scoring/feedback pipeline.

Every persisted score and feedback doc carries these so a later model change is
auditable and old results remain interpretable. Bump the relevant constant when
its component's behavior changes.
"""

RUBRIC_VERSION = "rubric-2026.05.1"
SCORING_MODEL_VERSION = "scoring-mock-1.0.0"
FEATURE_EXTRACTOR_VERSION = "features-mock-1.0.0"
PROMPT_VERSION = "prompt-mock-1.0.0"


def version_stamp() -> dict[str, str]:
    """Return the four version fields stamped onto sessions and feedback."""
    return {
        "rubric_version": RUBRIC_VERSION,
        "scoring_model_version": SCORING_MODEL_VERSION,
        "feature_extractor_version": FEATURE_EXTRACTOR_VERSION,
        "prompt_version": PROMPT_VERSION,
    }

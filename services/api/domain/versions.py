"""Pinned version identifiers for the scoring/feedback pipeline.

Every persisted score and feedback doc carries these so a later model change is
auditable and old results remain interpretable. Bump the relevant constant when
its component's behavior changes.
"""

RUBRIC_VERSION = "rubric-2026.05.1"
SCORING_MODEL_VERSION = "scoring-mock-1.0.0"
FEATURE_EXTRACTOR_VERSION = "features-mock-1.0.0"
PROMPT_VERSION = "prompt-mock-1.0.0"

# Persona path (acoustic scoring) versions — deliberately distinct from the
# Mode A/B set so a bump to one path never invalidates the other's golden, and a
# persisted persona score always says which acoustic rubric/scorer produced it.
PERSONA_RUBRIC_VERSION = "persona-rubric-2026.05.1"
PERSONA_SCORING_VERSION = "persona-acoustic-1.0.0"
ACOUSTIC_FEATURE_VERSION = "acoustic-features-1.0.0"
PERSONA_PROMPT_VERSION = "persona-feedback-1.0.0"


def version_stamp() -> dict[str, str]:
    """Return the four version fields stamped onto sessions and feedback."""
    return {
        "rubric_version": RUBRIC_VERSION,
        "scoring_model_version": SCORING_MODEL_VERSION,
        "feature_extractor_version": FEATURE_EXTRACTOR_VERSION,
        "prompt_version": PROMPT_VERSION,
    }


def persona_version_stamp() -> dict[str, str]:
    """Version fields for the persona (acoustic) scoring path.

    Same four keys as ``version_stamp`` (so persistence + the response model are
    unchanged), but distinct values identifying the acoustic rubric, scorer,
    feature set, and feedback prompt.
    """
    return {
        "rubric_version": PERSONA_RUBRIC_VERSION,
        "scoring_model_version": PERSONA_SCORING_VERSION,
        "feature_extractor_version": ACOUSTIC_FEATURE_VERSION,
        "prompt_version": PERSONA_PROMPT_VERSION,
    }

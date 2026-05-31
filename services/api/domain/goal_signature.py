"""Goal Signature: the personalization input that re-weights the rubric.

A learner's objective/occasion/audience/style shifts which capabilities matter.
A wedding toast weights engagement and confidence; an investor pitch weights
conciseness and clarity. Weights are normalized to mean 1.0 so the overall
score stays comparable across different goals.
"""

from dataclasses import dataclass, field

CANONICAL_CAPABILITIES = [
    "clarity",
    "pace",
    "fluency",
    "confidence",
    "engagement",
    "conciseness",
]

# Keyword → capability boosts. Matched (case-insensitively) against the
# concatenated Goal Signature text. Multiple matches stack before normalization.
_BOOST_RULES: list[tuple[tuple[str, ...], dict[str, float]]] = [
    (("pitch", "investor", "sales", "demo"), {"conciseness": 0.6, "clarity": 0.4}),
    (("toast", "wedding", "celebration", "story"), {"engagement": 0.6, "confidence": 0.4}),
    (("interview", "panel", "q&a", "qa"), {"confidence": 0.5, "fluency": 0.3}),
    (("lecture", "teach", "training", "explain"), {"clarity": 0.5, "pace": 0.3}),
    (("address", "keynote", "speech", "rally"), {"engagement": 0.4, "confidence": 0.4}),
    (("standup", "update", "briefing", "status"), {"conciseness": 0.5, "pace": 0.3}),
]


@dataclass(frozen=True)
class GoalSignature:
    """Immutable personalization profile for a single practice session."""

    objective: str = ""
    occasion: str = ""
    audience: str = ""
    style: str = ""
    language: str = "en"
    duration_seconds: int | None = None
    _extra: dict = field(default_factory=dict, compare=False)

    @classmethod
    def from_dict(cls, data: dict | None) -> "GoalSignature":
        data = data or {}
        known = {"objective", "occasion", "audience", "style", "language", "duration_seconds"}
        extra = {k: v for k, v in data.items() if k not in known}
        return cls(
            objective=data.get("objective", "") or "",
            occasion=data.get("occasion", "") or "",
            audience=data.get("audience", "") or "",
            style=data.get("style", "") or "",
            language=data.get("language", "en") or "en",
            duration_seconds=data.get("duration_seconds"),
            _extra=extra,
        )

    def to_dict(self) -> dict:
        return {
            "objective": self.objective,
            "occasion": self.occasion,
            "audience": self.audience,
            "style": self.style,
            "language": self.language,
            "duration_seconds": self.duration_seconds,
        }

    def text_blob(self) -> str:
        """Lowercased concatenation of all free-text fields, for keyword matching."""
        return " ".join([self.objective, self.occasion, self.audience, self.style]).lower()


def capability_weights(gs: GoalSignature) -> dict[str, float]:
    """Map a Goal Signature to per-capability weights, normalized to mean 1.0.

    Every canonical capability starts at weight 1.0; matching keyword rules add
    boosts. Final weights are rescaled so their mean is exactly 1.0, keeping the
    weighted overall score on the same 0–1 scale regardless of goal.
    """
    weights = {cap: 1.0 for cap in CANONICAL_CAPABILITIES}
    blob = gs.text_blob()
    for keywords, boosts in _BOOST_RULES:
        if any(kw in blob for kw in keywords):
            for cap, amount in boosts.items():
                weights[cap] += amount
    mean = sum(weights.values()) / len(weights)
    if mean <= 0:
        return {cap: 1.0 for cap in CANONICAL_CAPABILITIES}
    return {cap: round(w / mean, 6) for cap, w in weights.items()}

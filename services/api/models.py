"""Pydantic request/response models for the coaching API.

Response models carry the pipeline version fields so every scored payload is
self-describing (which rubric/model produced it). These are the wire contract;
the domain layer uses plain dataclasses internally.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class GoalSignatureModel(BaseModel):
    objective: str = ""
    occasion: str = ""
    audience: str = ""
    style: str = ""
    language: str = "en"
    duration_seconds: int | None = None


class CreateSessionRequest(BaseModel):
    user_id: str
    mode: Literal["guided", "user_script"]
    script_id: str | None = None  # required for mode="guided"
    script_text: str | None = None  # required for mode="user_script"
    goal_signature: GoalSignatureModel | None = None


class UtteranceInput(BaseModel):
    line_index: int
    audio_base64: str | None = None  # raw recording; mock STT ignores its content


class SubmitUtterancesRequest(BaseModel):
    utterances: list[UtteranceInput]


class RetryRequest(BaseModel):
    utterances: list[UtteranceInput]


class ImprovementModel(BaseModel):
    capability: str
    message: str
    severity: str
    line_index: int | None = None


class CorrectionModel(BaseModel):
    line_index: int
    focus_capability: str
    original_text: str
    corrected_text: str
    explanation: str
    user_audio_key: str | None = None
    ideal_audio_key: str | None = None


class FeedbackModel(BaseModel):
    summary: str
    strengths: list[str]
    improvements: list[ImprovementModel]
    read_aloud_text: str


class VersionsModel(BaseModel):
    rubric_version: str
    scoring_model_version: str
    feature_extractor_version: str
    prompt_version: str


class SessionDetail(BaseModel):
    session_id: str
    user_id: str
    mode: str
    status: str
    script_id: str | None = None
    expected_units: list[str] = []
    goal_signature: GoalSignatureModel = GoalSignatureModel()
    attempt: int = 1
    parent_session_id: str | None = None
    overall_score: float | None = None
    capability_scores: dict[str, float] = {}
    versions: VersionsModel | None = None
    feedback: FeedbackModel | None = None
    corrections: list[CorrectionModel] = []
    delta: dict[str, float] | None = None
    created_at: datetime | None = None


class ScriptLineModel(BaseModel):
    line_index: int
    text: str
    coaching_focus: list[str] = []


class ScriptSummary(BaseModel):
    script_id: str
    title: str
    language: str | None = None
    difficulty: str | None = None
    line_count: int


class ScriptDetail(BaseModel):
    script_id: str
    title: str
    description: str | None = None
    language: str | None = None
    difficulty: str | None = None
    estimated_duration_seconds: int | None = None
    goal_profile: dict | None = None
    target_capabilities: list[str] = []
    lines: list[ScriptLineModel]


# ---- personas (20 Legends) -------------------------------------------------


class PersonaReference(BaseModel):
    title: str | None = None
    video_url: str | None = None


class PersonaSummary(BaseModel):
    persona_id: str
    name: str
    role: str | None = None
    archetype: str | None = None
    line_count: int


class PersonaRubricView(BaseModel):
    """The demo-relevant slice of a persona rubric (scoring weights stay server-side)."""

    target_pace_sps: list[float] = []
    expressiveness: str | None = None
    pause_style: str | None = None


class PersonaDetail(BaseModel):
    persona_id: str
    name: str
    role: str | None = None
    archetype: str | None = None
    reference: PersonaReference | None = None
    goal_line: str | None = None
    signature_qualities: list[str] = []
    estimated_duration_seconds: int | None = None
    lines: list[ScriptLineModel]
    rubric: PersonaRubricView | None = None

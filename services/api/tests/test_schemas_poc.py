"""Validate the 11 POC collection schemas: well-formed, structurally correct."""

import json
from pathlib import Path

SCHEMAS_DIR = Path(__file__).resolve().parents[1] / "db" / "schemas"

EXPECTED_SCHEMAS = {
    "users",
    "learner_profiles",
    "guided_scripts",
    "personas",
    "practice_sessions",
    "session_utterances",
    "coaching_feedback",
    "audio_corrections",
    "progress_snapshots",
    "model_eval_runs",
    "release_health_events",
}

SCHEMA_FILES = sorted(SCHEMAS_DIR.glob("*.json"))


def _load(name: str) -> dict:
    return json.loads((SCHEMAS_DIR / f"{name}.json").read_text(encoding="utf-8"))


def test_all_expected_schemas_present():
    names = {p.stem for p in SCHEMA_FILES}
    assert EXPECTED_SCHEMAS <= names, f"Missing: {EXPECTED_SCHEMAS - names}"


def test_all_schema_files_parse_as_json():
    errors = []
    for path in SCHEMA_FILES:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"{path.name}: {e}")
    assert errors == [], "\n".join(errors)


def test_all_schemas_have_json_schema_key():
    missing = [p.name for p in SCHEMA_FILES if "$jsonSchema" not in _load(p.stem)]
    assert not missing, f"Missing $jsonSchema: {missing}"


def test_every_schema_requires_audit_fields():
    # created_at + schema_version are mandatory on every collection (core data rule).
    offenders = []
    for name in EXPECTED_SCHEMAS:
        required = _load(name)["$jsonSchema"]["required"]
        for field in ("created_at", "schema_version"):
            if field not in required:
                offenders.append(f"{name}: missing required {field}")
    assert not offenders, offenders


def test_practice_sessions_has_version_fields():
    props = _load("practice_sessions")["$jsonSchema"]["properties"]
    for field in (
        "rubric_version",
        "scoring_model_version",
        "feature_extractor_version",
        "prompt_version",
    ):
        assert field in props, f"practice_sessions missing version field: {field}"


def test_practice_sessions_mode_and_status_enums():
    props = _load("practice_sessions")["$jsonSchema"]["properties"]
    assert set(props["mode"]["enum"]) == {"guided", "user_script", "persona"}
    for expected in ("created", "processing", "scored", "failed"):
        assert expected in props["status"]["enum"]


def test_coaching_feedback_has_version_fields():
    props = _load("coaching_feedback")["$jsonSchema"]["properties"]
    for field in (
        "rubric_version",
        "scoring_model_version",
        "feature_extractor_version",
        "prompt_version",
    ):
        assert field in props


def test_guided_scripts_lines_structure():
    props = _load("guided_scripts")["$jsonSchema"]["properties"]
    line_props = props["lines"]["items"]["properties"]
    assert "line_index" in line_props
    assert "text" in line_props


def test_personas_schema_structure():
    schema = _load("personas")["$jsonSchema"]
    for field in ("persona_id", "name", "speech", "rubric"):
        assert field in schema["required"], f"personas must require {field}"
    props = schema["properties"]
    line_props = props["speech"]["properties"]["lines"]["items"]["properties"]
    assert "line_index" in line_props and "text" in line_props
    rubric = props["rubric"]["properties"]
    assert "capability_weights" in rubric and "target_pace_sps" in rubric
    assert set(rubric["expressiveness"]["enum"]) == {"monotone", "balanced", "high-contrast"}
    assert set(rubric["pause_style"]["enum"]) == {"steady", "dramatic", "brisk"}


def test_score_fields_are_bounded():
    # overall_score must be a nullable double bounded to [0, 1] wherever present.
    for name in ("practice_sessions", "coaching_feedback", "progress_snapshots"):
        score = _load(name)["$jsonSchema"]["properties"]["overall_score"]
        assert score.get("minimum") == 0 and score.get("maximum") == 1, name

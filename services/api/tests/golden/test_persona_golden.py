"""Golden-dataset regression test for the persona (acoustic) scoring path.

The mock acoustic stack is fully deterministic, so a persona run's scores are a
fixed function of its inputs. `persona_dataset.json` pins the expected overall,
`style_match`, and per-capability scores for representative speakers; this test
fails if a code change shifts any score beyond `tolerance`, drops below the
model-quality floor, or bumps a persona `*_version` without a regenerated
dataset. That makes acoustic scoring-behavior changes explicit and reviewable.

It is deliberately separate from `test_golden_regression.py`: the two paths carry
distinct `*_version` fields and distinct golden sets, so a bump to one never
invalidates the other.

The persona scorer reads the *raw waveform*, so — unlike the transcript path — it
honors audio presence: a recorded line needs stored bytes, a skipped line has
none (and drags coverage). The test reproduces that by storing a blob for each
`recorded_lines` index, exactly as the real submit flow would.

Regenerating after an intentional persona version bump: run
``.venv-poc/bin/python`` over the cases (see ``_run_case`` below), build a
pipeline with ``CoachingPipeline(build_providers(<mock Settings>,
store=InMemoryObjectStore()))``, call ``run_persona`` per case, paste the new
``round(value, 6)`` numbers back into ``persona_dataset.json``, and bump its
version fields + ``persona_model_quality`` in ``quality-baseline.poc.json`` to
match ``domain/versions.py``. A diff in the dataset is a scoring-behavior change.
"""

import json
from pathlib import Path
from uuid import uuid4

from services.api import repository as repo
from services.api.domain import versions
from services.api.domain.persona import PersonaRubric
from services.api.domain.pipeline import CoachingPipeline
from services.api.providers.object_store import InMemoryObjectStore
from services.api.providers.registry import build_providers

_DATASET = Path(__file__).with_name("persona_dataset.json")
_BASELINE = Path(__file__).resolve().parents[4] / "quality-baseline.poc.json"


class _Settings:
    provider_stt = "mock"
    provider_tts = "mock"
    provider_llm = "mock"
    provider_acoustic = "mock"
    object_store = "memory"
    poc_storage_dir = "./.poc-storage"


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def _pipeline() -> CoachingPipeline:
    return CoachingPipeline(build_providers(_Settings(), store=InMemoryObjectStore()))


def _run_case(pipe: CoachingPipeline, case: dict):
    """Replay one golden case: store audio for recorded lines, then run_persona."""
    recorded = set(case["recorded_lines"])
    utterances = []
    for i in range(len(case["expected_units"])):
        if i in recorded:
            key = f"sessions/{case['id']}/utterances/{i}.wav"
            pipe.p.store.put(key, b"\x01" * 32)  # mock ignores content, honors presence
            utterances.append({"line_index": i, "audio_key": key})
        else:
            utterances.append({"line_index": i, "audio_key": None})  # skipped → coverage drag
    return pipe.run_persona(
        session_id=case["id"],
        persona_name=case["persona_name"],
        rubric=PersonaRubric.from_dict(case["rubric"]),
        expected_units=case["expected_units"],
        utterances=utterances,
    )


def test_persona_dataset_version_matches_pipeline():
    """A persona model/rubric bump must be accompanied by a regenerated dataset."""
    data = _load(_DATASET)
    assert data["scoring_model_version"] == versions.PERSONA_SCORING_VERSION
    assert data["rubric_version"] == versions.PERSONA_RUBRIC_VERSION


def test_persona_baseline_declares_consistent_model_quality():
    """The committed POC baseline must reference the same persona golden + versions."""
    baseline = _load(_BASELINE)["persona_model_quality"]
    data = _load(_DATASET)
    assert baseline["golden_set_id"] == data["golden_set_id"]
    assert baseline["scoring_model_version"] == versions.PERSONA_SCORING_VERSION
    assert baseline["rubric_version"] == versions.PERSONA_RUBRIC_VERSION


def test_persona_golden_scores_within_tolerance_and_above_floor(db):
    data = _load(_DATASET)
    baseline = _load(_BASELINE)["persona_model_quality"]
    tolerance = data["tolerance"]
    floor = baseline["min_overall_score"]
    pipe = _pipeline()

    abs_errors: list[float] = []
    for case in data["cases"]:
        result = _run_case(pipe, case)
        assert result.status == "scored", case["id"]
        assert result.style_match is not None, case["id"]
        assert result.acoustic is not None, case["id"]

        exp = case["expected"]
        overall_err = abs(result.overall_score - exp["overall"])
        assert overall_err <= tolerance, f"{case['id']} overall drifted by {overall_err}"
        assert result.overall_score >= floor, f"{case['id']} below quality floor {floor}"
        abs_errors.append(overall_err)

        style_err = abs(result.style_match - exp["style_match"])
        assert style_err <= tolerance, f"{case['id']} style_match drifted by {style_err}"
        abs_errors.append(style_err)

        assert set(result.capability_scores) == set(exp["capabilities"]), case["id"]
        for cap, expected_score in exp["capabilities"].items():
            err = abs(result.capability_scores[cap] - expected_score)
            assert err <= tolerance, f"{case['id']}.{cap} drifted by {err}"
            abs_errors.append(err)

    mae = sum(abs_errors) / len(abs_errors)
    assert mae <= baseline["max_mean_absolute_error"]

    # Record the run exactly as ops would for a real golden evaluation.
    run = repo.save_eval_run(
        db,
        {
            "run_id": uuid4().hex,
            "scoring_model_version": versions.PERSONA_SCORING_VERSION,
            "rubric_version": versions.PERSONA_RUBRIC_VERSION,
            "golden_set_id": data["golden_set_id"],
            "sample_count": len(data["cases"]),
            "mean_absolute_error": float(mae),
            "min_golden_score": float(min(c["expected"]["overall"] for c in data["cases"])),
            "passed": True,
            "metrics": {"tolerance": tolerance},
        },
    )
    assert run["passed"] is True
    assert run["created_at"] and run["schema_version"] == repo.SCHEMA_VERSION
    assert db.model_eval_runs.count_documents({}) == 1

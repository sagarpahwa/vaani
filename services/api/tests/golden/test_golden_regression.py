"""Golden-dataset regression test for the coaching pipeline.

The mock provider stack is fully deterministic, so the pipeline's scores are a
fixed function of its inputs. `dataset.json` pins the expected overall +
per-capability scores for a handful of representative sessions; this test fails
if a code change shifts any score beyond `tolerance`. That makes scoring
behavior changes explicit and reviewable instead of silent.

It also enforces the model-quality floor declared in `quality-baseline.poc.json`
(`model_quality.min_overall_score`) and records a `model_eval_runs` document, the
same shape ops would persist for a real golden run.

Regenerating after an intentional version bump: build a pipeline with
``CoachingPipeline(build_providers(<mock Settings>, store=InMemoryObjectStore()))``
(see ``_pipeline()`` below), run each case in ``dataset.json``, paste the new
``round(overall, 6)`` + per-capability values back into that file, and bump its
``scoring_model_version`` / ``rubric_version`` to match ``domain/versions.py``.
A diff in the dataset is a scoring-behavior change and must be reviewed.
"""

import json
from pathlib import Path
from uuid import uuid4

from services.api import repository as repo
from services.api.domain import versions
from services.api.domain.goal_signature import GoalSignature
from services.api.domain.pipeline import CoachingPipeline
from services.api.providers.object_store import InMemoryObjectStore
from services.api.providers.registry import build_providers

_DATASET = Path(__file__).with_name("dataset.json")
_BASELINE = Path(__file__).resolve().parents[4] / "quality-baseline.poc.json"


class _Settings:
    provider_stt = "mock"
    provider_tts = "mock"
    provider_llm = "mock"
    object_store = "memory"
    poc_storage_dir = "./.poc-storage"


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def _pipeline() -> CoachingPipeline:
    return CoachingPipeline(build_providers(_Settings(), store=InMemoryObjectStore()))


def test_dataset_version_matches_pipeline():
    """A model/rubric bump must be accompanied by a regenerated golden dataset."""
    data = _load(_DATASET)
    assert data["scoring_model_version"] == versions.SCORING_MODEL_VERSION
    assert data["rubric_version"] == versions.RUBRIC_VERSION


def test_baseline_declares_consistent_model_quality():
    """The committed POC baseline must reference the same golden set + versions."""
    baseline = _load(_BASELINE)["model_quality"]
    data = _load(_DATASET)
    assert baseline["golden_set_id"] == data["golden_set_id"]
    assert baseline["scoring_model_version"] == versions.SCORING_MODEL_VERSION


def test_golden_scores_within_tolerance_and_above_floor(db):
    data = _load(_DATASET)
    baseline = _load(_BASELINE)["model_quality"]
    tolerance = data["tolerance"]
    floor = baseline["min_overall_score"]
    pipe = _pipeline()

    abs_errors: list[float] = []
    for case in data["cases"]:
        result = pipe.run(
            session_id=case["id"],
            goal=GoalSignature.from_dict(case["goal"]),
            expected_units=case["expected_units"],
            utterances=case["utterances"],
        )
        assert result.status == "scored", case["id"]

        exp = case["expected"]
        overall_err = abs(result.overall_score - exp["overall"])
        assert overall_err <= tolerance, f"{case['id']} overall drifted by {overall_err}"
        assert result.overall_score >= floor, f"{case['id']} below quality floor {floor}"
        abs_errors.append(overall_err)

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
            "scoring_model_version": versions.SCORING_MODEL_VERSION,
            "rubric_version": versions.RUBRIC_VERSION,
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

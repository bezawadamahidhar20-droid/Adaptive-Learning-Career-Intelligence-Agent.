"""
Calibration Split, Generalization Metrics & Artifact Regeneration Tests
Covers the train/held-out separation, the threshold-free metrics, and the
startup self-healing path that regenerates a missing artifact.
"""
import csv
import json
import os

import pytest

from agent.knowledge.bkt import load_concept_params
from agent.analytics.train_calibration import (
    ModelCalibrator,
    ensure_calibration_artifact,
    train_and_save,
)

CONCEPTS = ["Alpha", "Beta", "Gamma"]
STUDENTS = 12
STEPS = 9


def write_dataset(path, flip_students=None):
    """Small deterministic dataset: correctness follows a fixed per-student pattern."""
    flip_students = flip_students or set()
    fieldnames = [
        "student_id", "step", "timestamp", "concept", "skill", "item_id",
        "irt_difficulty_b", "irt_discrimination_a", "student_theta",
        "prior_mastery", "is_correct", "response_time_sec",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for i in range(STUDENTS):
            student_id = f"STU_{i:03d}"
            for step in range(STEPS):
                concept = CONCEPTS[(i + step) % len(CONCEPTS)]
                is_correct = 1 if (i + step) % 3 != 0 else 0
                if student_id in flip_students:
                    is_correct = 1 - is_correct
                writer.writerow({
                    "student_id": student_id,
                    "step": step,
                    "timestamp": "2026-01-01T09:00:00+00:00",
                    "concept": concept,
                    "skill": f"Skill-{concept}",
                    "item_id": f"ITEM_{concept}_{step}",
                    "irt_difficulty_b": 0.0,
                    "irt_discrimination_a": 1.2,
                    "student_theta": 0.0,
                    "prior_mastery": 0.3,
                    "is_correct": is_correct,
                    "response_time_sec": 30,
                })
    return str(path)


@pytest.fixture
def dataset_path(tmp_path):
    return write_dataset(tmp_path / "logs.csv")


# ------------------------------------------------------------------ splitting

def test_split_keeps_students_disjoint(dataset_path):
    calibrator = ModelCalibrator(dataset_path, benchmarks_path=None, holdout_ratio=0.25, seed=7)

    train_ids = set(r["student_id"] for r in calibrator.train_interactions)
    holdout_ids = set(r["student_id"] for r in calibrator.holdout_interactions)

    assert train_ids & holdout_ids == set()
    assert train_ids | holdout_ids == set(r["student_id"] for r in calibrator.interactions)
    assert len(train_ids) + len(holdout_ids) == STUDENTS
    assert len(calibrator.holdout_students) == len(holdout_ids)
    assert len(calibrator.train_interactions) + len(calibrator.holdout_interactions) == len(
        calibrator.interactions
    )


def test_split_is_deterministic_for_a_given_seed(dataset_path):
    a = ModelCalibrator(dataset_path, benchmarks_path=None, holdout_ratio=0.25, seed=7)
    b = ModelCalibrator(dataset_path, benchmarks_path=None, holdout_ratio=0.25, seed=7)
    assert a.holdout_students == b.holdout_students


def test_calibration_ignores_held_out_labels(tmp_path):
    """Flipping held-out labels must not move the fitted parameters (i.e. no leakage)."""
    clean_path = write_dataset(tmp_path / "clean.csv")
    clean = ModelCalibrator(clean_path, benchmarks_path=None, holdout_ratio=0.25, seed=7)
    clean_params = clean.train_all_concepts()

    flipped_path = write_dataset(tmp_path / "flipped.csv", flip_students=set(clean.holdout_students))
    flipped = ModelCalibrator(flipped_path, benchmarks_path=None, holdout_ratio=0.25, seed=7)
    flipped_params = flipped.train_all_concepts()

    # Same students held out, training rows untouched, identical parameters
    assert flipped.holdout_students == clean.holdout_students
    assert [r["is_correct"] for r in flipped.train_interactions] == [
        r["is_correct"] for r in clean.train_interactions
    ]
    assert flipped_params == clean_params


# --------------------------------------------------------------------- metrics

def test_metrics_auc_accuracy_and_baselines():
    probs = [0.9, 0.8, 0.2, 0.1]
    actuals = [1, 1, 0, 0]

    metrics = ModelCalibrator.compute_metrics(probs, actuals)
    assert metrics["auc"] == pytest.approx(1.0)
    assert metrics["accuracy_percentage"] == pytest.approx(100.0)
    assert metrics["predicted_positive_rate"] == pytest.approx(0.5)
    assert metrics["constant_majority_baseline_accuracy"] == pytest.approx(50.0)

    # Inverted ranking
    assert ModelCalibrator.compute_metrics([0.1, 0.2, 0.8, 0.9], actuals)["auc"] == pytest.approx(0.0)

    # All predictions tied -> AUC 0.5 (no division by zero)
    assert ModelCalibrator.compute_metrics([0.5] * 4, actuals)["auc"] == pytest.approx(0.5)

    # A constant predictor can only match the majority-class baseline
    constant = ModelCalibrator.compute_metrics([0.1] * 4, actuals)
    assert constant["accuracy_percentage"] == constant["constant_majority_baseline_accuracy"]

    # Uneven base rates: majority baseline is the larger class
    skewed = ModelCalibrator.compute_metrics([0.1] * 7 + [0.9] * 3, [0] * 7 + [1] * 3)
    assert skewed["constant_majority_baseline_accuracy"] == pytest.approx(70.0)

    # Empty split degrades gracefully
    assert ModelCalibrator.compute_metrics([], []) == {"total_interactions_evaluated": 0}


def test_concept_majority_baseline_uses_train_rates():
    probs = [0.9, 0.9, 0.9, 0.9]
    actuals = [1, 1, 0, 0]
    concepts = ["Alpha", "Alpha", "Beta", "Beta"]

    # Training says most Alpha responses are correct and most Beta responses are not,
    # so the per-concept baseline is right on both while a constant predictor is not.
    rates = {"Alpha": 0.9, "Beta": 0.1}
    metrics = ModelCalibrator.compute_metrics(probs, actuals, concepts=concepts, concept_baseline_rates=rates)
    assert metrics["concept_majority_baseline_accuracy"] == pytest.approx(100.0)
    assert metrics["constant_majority_baseline_accuracy"] == pytest.approx(50.0)


# ---------------------------------------------------------------- evaluation

def test_evaluation_covers_each_split_separately(dataset_path):
    calibrator = ModelCalibrator(dataset_path, benchmarks_path=None, holdout_ratio=0.25, seed=7)
    params = calibrator.train_all_concepts()

    train_metrics = calibrator.evaluate_prediction_accuracy(params, calibrator.train_interactions)
    holdout_metrics = calibrator.evaluate_prediction_accuracy(params, calibrator.holdout_interactions)

    assert train_metrics["total_interactions_evaluated"] == len(calibrator.train_interactions)
    assert holdout_metrics["total_interactions_evaluated"] == len(calibrator.holdout_interactions)
    assert holdout_metrics["auc"] is not None
    assert "concept_majority_baseline_accuracy" in holdout_metrics


def test_blend_weight_is_fit_on_training_rows_only(tmp_path):
    """Flipping held-out labels must not change the fitted blend weight either."""
    clean_path = write_dataset(tmp_path / "clean.csv")
    clean = ModelCalibrator(clean_path, benchmarks_path=None, holdout_ratio=0.25, seed=7)
    clean_params = clean.train_all_concepts()
    clean_weight, clean_metrics = clean.fit_irt_blend_weight(clean_params)

    flipped_path = write_dataset(tmp_path / "flipped.csv", flip_students=set(clean.holdout_students))
    flipped = ModelCalibrator(flipped_path, benchmarks_path=None, holdout_ratio=0.25, seed=7)
    flipped_params = flipped.train_all_concepts()
    flipped_weight, _ = flipped.fit_irt_blend_weight(flipped_params)

    assert 0.0 <= clean_weight <= 1.0
    assert clean_metrics["total_interactions_evaluated"] == len(clean.train_interactions)
    assert flipped_weight == clean_weight


def test_blended_evaluation_covers_the_holdout_split(dataset_path):
    calibrator = ModelCalibrator(dataset_path, benchmarks_path=None, holdout_ratio=0.25, seed=7)
    params = calibrator.train_all_concepts()
    weight, _ = calibrator.fit_irt_blend_weight(params)

    blended = calibrator.evaluate_prediction_accuracy(
        params, calibrator.holdout_interactions, irt_weight=weight
    )
    assert blended["total_interactions_evaluated"] == len(calibrator.holdout_interactions)
    assert blended["auc"] is not None

    # irt_weight=0.0 must reproduce the pure BKT prediction exactly
    explicit = calibrator.evaluate_prediction_accuracy(
        params, calibrator.holdout_interactions, irt_weight=0.0
    )
    default = calibrator.evaluate_prediction_accuracy(params, calibrator.holdout_interactions)
    assert explicit == default

    # A pure IRT prediction stays a valid probability
    pure_irt = calibrator.evaluate_prediction_accuracy(
        params, calibrator.holdout_interactions, irt_weight=1.0
    )
    assert 0.0 <= pure_irt["predicted_positive_rate"] <= 1.0


def test_train_and_save_persists_split_config_and_both_splits_metrics(tmp_path, dataset_path):
    artifact = str(tmp_path / "artifact.json")
    result = train_and_save(dataset_path=dataset_path, artifact_path=artifact, verbose=False)

    assert result["artifact_path"] == artifact
    assert load_concept_params(artifact) == result["calibrated_params"]

    payload = json.loads(open(artifact, encoding="utf-8").read())
    assert payload["version"] == 1

    split = payload["metadata"]["split"]
    assert split["method"] == "student_level_holdout"
    assert split["train_students"] + split["holdout_students"] == STUDENTS
    assert split["train_students"] > 0 and split["holdout_students"] > 0

    metrics = payload["metadata"]["metrics"]
    assert payload["metadata"]["irt_blend_weight"] == result["irt_blend_weight"]

    bkt = metrics["bkt_only"]
    assert bkt["train"]["total_interactions_evaluated"] == split["train_interactions"]
    assert bkt["holdout"]["total_interactions_evaluated"] == split["holdout_interactions"]
    assert bkt["all"]["total_interactions_evaluated"] == (
        split["train_interactions"] + split["holdout_interactions"]
    )
    assert bkt["holdout"]["accuracy_percentage"] is not None
    assert bkt["holdout"]["auc"] is not None
    assert metrics["blended"]["holdout"]["auc"] is not None


# ------------------------------------------------- artifact self-healing path

def test_ensure_artifact_regenerates_when_missing(tmp_path, dataset_path):
    artifact = str(tmp_path / "missing_artifact.json")
    assert not os.path.exists(artifact)

    resolved = ensure_calibration_artifact(dataset_path=dataset_path, artifact_path=artifact, verbose=False)

    assert resolved == artifact
    assert os.path.exists(artifact)
    assert len(load_concept_params(artifact)) == len(CONCEPTS)


def test_ensure_artifact_replaces_a_corrupt_artifact(tmp_path, dataset_path):
    """A present-but-corrupt artifact must self-heal, not be trusted by the existence check."""
    artifact = tmp_path / "corrupt.json"
    artifact.write_text("{ this is not valid json", encoding="utf-8")

    resolved = ensure_calibration_artifact(
        dataset_path=dataset_path, artifact_path=str(artifact), verbose=False
    )

    assert resolved == str(artifact)
    # Now genuinely loadable, with the full concept set
    assert len(load_concept_params(str(artifact))) == len(CONCEPTS)


def test_ensure_artifact_replaces_an_empty_artifact(tmp_path, dataset_path):
    """Valid JSON with no concepts is unusable in practice and must also be rebuilt."""
    artifact = tmp_path / "empty.json"
    artifact.write_text(
        json.dumps({"version": 1, "metadata": {}, "concepts": {}}), encoding="utf-8"
    )

    resolved = ensure_calibration_artifact(
        dataset_path=dataset_path, artifact_path=str(artifact), verbose=False
    )

    assert resolved == str(artifact)
    assert len(load_concept_params(str(artifact))) == len(CONCEPTS)


def test_ensure_artifact_is_a_noop_when_present(tmp_path, dataset_path):
    artifact = tmp_path / "present.json"
    sentinel = {
        "version": 1,
        "metadata": {"keep": True},
        "concepts": {"Alpha": {"p_init": 0.2, "p_transit": 0.2, "p_guess": 0.2, "p_slip": 0.1}},
    }
    artifact.write_text(json.dumps(sentinel), encoding="utf-8")

    resolved = ensure_calibration_artifact(
        dataset_path=dataset_path, artifact_path=str(artifact), verbose=False
    )

    assert resolved == str(artifact)
    # Untouched: no retraining happened
    assert json.loads(artifact.read_text(encoding="utf-8")) == sentinel


def test_ensure_artifact_returns_none_without_dataset(tmp_path):
    resolved = ensure_calibration_artifact(
        dataset_path=str(tmp_path / "absent.csv"),
        artifact_path=str(tmp_path / "absent.json"),
        verbose=False,
    )
    assert resolved is None

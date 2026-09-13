"""
Calibration Artifact Persistence & Live Wiring Tests
Verifies that parameters calibrated offline are saved, reloaded, and actually
used by the live AdaptiveLearningAgent (with a safe fallback to defaults).
"""
import json

import pytest

from agent.knowledge.bkt import (
    BKTKnowledgeTracer,
    BKTParameters,
    load_calibration_metadata,
    load_concept_params,
    save_concept_params,
)
from agent.agent import AdaptiveLearningAgent, DEFAULT_IRT_BLEND_WEIGHT


def test_bkt_parameters_dict_round_trip():
    params = BKTParameters(p_init=0.35, p_transit=0.28, p_guess=0.25, p_slip=0.08)
    restored = BKTParameters.from_dict(params.to_dict())
    assert restored == params

    with pytest.raises(ValueError):
        BKTParameters.from_dict({"p_init": 1.5, "p_transit": 0.2, "p_guess": 0.2, "p_slip": 0.1})


def test_save_and_load_concept_params_round_trip(tmp_path):
    path = str(tmp_path / "calibrated_bkt_params.json")
    calibrated = {
        "Python": BKTParameters(p_init=0.35, p_transit=0.28, p_guess=0.25, p_slip=0.08),
        "SQL": BKTParameters(p_init=0.25, p_transit=0.12, p_guess=0.20, p_slip=0.14),
    }

    written = save_concept_params(calibrated, path=path, metadata={"concepts_calibrated": 2})
    assert written == path

    loaded = load_concept_params(path)
    assert loaded == calibrated
    assert load_calibration_metadata(path)["concepts_calibrated"] == 2


def test_load_missing_artifact_returns_empty(tmp_path):
    missing = str(tmp_path / "does_not_exist.json")
    assert load_concept_params(missing) == {}
    assert load_calibration_metadata(missing) == {}


def test_load_corrupt_artifact_falls_back_to_defaults(tmp_path):
    path = tmp_path / "corrupt.json"
    path.write_text("{ not valid json", encoding="utf-8")

    assert load_concept_params(str(path)) == {}
    with pytest.raises(json.JSONDecodeError):
        load_concept_params(str(path), strict=True)


def test_load_artifact_with_out_of_range_params_is_skipped(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps({
        "version": 1,
        "metadata": {},
        "concepts": {"Python": {"p_init": 2.0, "p_transit": 0.2, "p_guess": 0.2, "p_slip": 0.1}},
    }), encoding="utf-8")

    assert load_concept_params(str(path)) == {}


def test_agent_uses_calibrated_parameters(tmp_path):
    # Discover a real concept from the shipped question bank
    reference_agent = AdaptiveLearningAgent(calibration_path=str(tmp_path / "absent.json"))
    assert reference_agent.calibrated_params == {}

    sample_question = reference_agent.question_bank[0]
    concept = sample_question["concept"]

    # A calibrated P(L0) that clearly differs from the BKTParameters() default of 0.1
    calibrated = {concept: BKTParameters(p_init=0.42, p_transit=0.28, p_guess=0.25, p_slip=0.08)}
    path = save_concept_params(calibrated, path=str(tmp_path / "calibrated.json"))

    agent = AdaptiveLearningAgent(calibration_path=path)
    assert agent.calibrated_params[concept].p_init == pytest.approx(0.42)
    assert agent.bkt.get_params(concept).p_init == pytest.approx(0.42)

    # Cold start for a concept with no recorded mastery must use the calibrated prior
    student = agent.initialize_student_profile()
    result = agent.process_answer(student, sample_question["id"], sample_question["answer"])
    assert result["previous_mastery"] == pytest.approx(0.42)

    # Uncalibrated concepts still fall back to the built-in defaults
    other_concept = next(
        q["concept"] for q in agent.question_bank if q["concept"] != concept
    )
    assert agent.bkt.get_params(other_concept) == BKTParameters()


def test_agent_without_artifact_uses_default_parameters(tmp_path):
    agent = AdaptiveLearningAgent(calibration_path=str(tmp_path / "absent.json"))
    tracer = BKTKnowledgeTracer(concept_params=agent.calibrated_params)
    assert tracer.get_params("Any Concept") == BKTParameters()
    assert agent.irt_blend_weight == DEFAULT_IRT_BLEND_WEIGHT


def test_agent_reads_blend_weight_from_calibration_metadata(tmp_path):
    fitted = str(tmp_path / "fitted.json")
    save_concept_params({}, path=fitted, metadata={"irt_blend_weight": 0.75})
    assert AdaptiveLearningAgent(calibration_path=fitted).irt_blend_weight == pytest.approx(0.75)

    # Clamped to [0, 1]
    clamped = str(tmp_path / "clamped.json")
    save_concept_params({}, path=clamped, metadata={"irt_blend_weight": 3.0})
    assert AdaptiveLearningAgent(calibration_path=clamped).irt_blend_weight == pytest.approx(1.0)

    # Non-numeric metadata falls back to the default rather than crashing startup
    bogus = str(tmp_path / "bogus.json")
    save_concept_params({}, path=bogus, metadata={"irt_blend_weight": "not-a-number"})
    assert AdaptiveLearningAgent(calibration_path=bogus).irt_blend_weight == DEFAULT_IRT_BLEND_WEIGHT


def test_predict_response_probability_blends_mastery_and_ability(tmp_path):
    agent = AdaptiveLearningAgent(calibration_path=str(tmp_path / "absent.json"))
    question = agent.question_bank[0]
    concept = question["concept"]

    student = agent.initialize_student_profile(initial_theta=2.0, prior_masteries={concept: 0.2})
    mastery_probability = agent.bkt.predict_correctness_probability(concept, 0.2)
    ability_probability = agent.irt.probability_correct(
        student["theta"], question["irt_a"], question["irt_b"]
    )
    # Sanity: the two signals must actually disagree for this test to mean anything
    assert mastery_probability != pytest.approx(ability_probability)

    assert agent.predict_response_probability(student, question["id"], irt_weight=0.0) == pytest.approx(
        mastery_probability
    )
    assert agent.predict_response_probability(student, question["id"], irt_weight=1.0) == pytest.approx(
        ability_probability
    )
    quarter = agent.predict_response_probability(student, question["id"], irt_weight=0.25)
    assert quarter == pytest.approx(0.25 * ability_probability + 0.75 * mastery_probability)
    assert min(mastery_probability, ability_probability) <= quarter <= max(
        mastery_probability, ability_probability
    )

    # Default (None) uses the weight loaded from the calibration artifact
    assert agent.predict_response_probability(student, question["id"]) == pytest.approx(
        agent.predict_response_probability(student, question["id"], irt_weight=agent.irt_blend_weight)
    )

    with pytest.raises(ValueError):
        agent.predict_response_probability(student, "Q_DOES_NOT_EXIST")

    # Unseen concept falls back to the calibrated cold-start prior, not a crash
    fresh = agent.initialize_student_profile()
    probability = agent.predict_response_probability(fresh, question["id"])
    assert 0.0 <= probability <= 1.0

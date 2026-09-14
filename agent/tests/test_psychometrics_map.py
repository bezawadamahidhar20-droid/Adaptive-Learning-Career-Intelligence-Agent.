"""
Unit Tests for MAP Ability Estimation & Psychometric Precision
"""
import pytest
from agent.psychometrics.estimation import MAPAbilityEstimator
from agent.psychometrics.irt import IRTModel


def test_map_estimator_zero_responses():
    estimator = MAPAbilityEstimator(prior_mean=0.0, prior_std=1.0)
    result = estimator.estimate([])
    assert result.theta == 0.0
    assert result.item_count == 0
    assert result.converged is True
    assert result.prior_information == 1.0
    assert result.posterior_se == 1.0


def test_map_estimator_all_correct():
    estimator = MAPAbilityEstimator(prior_mean=0.0, prior_std=1.0)
    responses = [
        {"difficulty": -1.0, "discrimination": 1.2, "is_correct": 1},
        {"difficulty": 0.0, "discrimination": 1.5, "is_correct": 1},
        {"difficulty": 1.0, "discrimination": 1.1, "is_correct": 1},
        {"difficulty": 1.5, "discrimination": 1.4, "is_correct": 1},
    ]
    result = estimator.estimate(responses)
    assert result.theta > 0.8
    assert result.converged is True
    assert result.posterior_se < 1.0
    assert result.observed_information > 0.0


def test_map_estimator_all_incorrect():
    estimator = MAPAbilityEstimator(prior_mean=0.0, prior_std=1.0)
    responses = [
        {"difficulty": -1.0, "discrimination": 1.2, "is_correct": 0},
        {"difficulty": 0.0, "discrimination": 1.5, "is_correct": 0},
        {"difficulty": 1.0, "discrimination": 1.1, "is_correct": 0},
    ]
    result = estimator.estimate(responses)
    assert result.theta < -0.5
    assert result.converged is True


def test_map_estimator_reproducibility():
    estimator = MAPAbilityEstimator(prior_mean=0.0, prior_std=1.0)
    responses = [
        {"difficulty": 0.0, "discrimination": 1.0, "is_correct": 1},
        {"difficulty": 0.5, "discrimination": 1.2, "is_correct": 0},
        {"difficulty": -0.5, "discrimination": 1.1, "is_correct": 1},
    ]
    res1 = estimator.estimate(responses, initial_theta=0.0)
    res2 = estimator.estimate(responses, initial_theta=0.0)
    assert res1.theta == res2.theta
    assert res1.posterior_se == res2.posterior_se
    assert res1.observed_information == res2.observed_information

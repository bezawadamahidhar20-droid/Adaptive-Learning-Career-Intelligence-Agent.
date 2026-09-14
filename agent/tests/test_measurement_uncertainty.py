"""
Unit Tests for Measurement Uncertainty & Reliability Engine
"""
import pytest
from agent.psychometrics.uncertainty import MeasurementUncertainty
from agent.psychometrics.estimation import AbilityEstimate


def test_credible_interval_bounds_and_ordering():
    theta = 0.50
    se = 0.25
    raw_ci, disp_ci, near_boundary = MeasurementUncertainty.calculate_credible_interval(theta, se)
    
    # Check ordering
    assert raw_ci[0] < theta < raw_ci[1]
    assert disp_ci[0] < theta < disp_ci[1]
    
    # Check 1.96 * 0.25 = 0.49
    assert abs(raw_ci[0] - 0.01) < 0.01
    assert abs(raw_ci[1] - 0.99) < 0.01
    assert near_boundary is False


def test_near_boundary_detection():
    theta_extreme = 3.8
    se = 0.30
    raw_ci, disp_ci, near_boundary = MeasurementUncertainty.calculate_credible_interval(theta_extreme, se)
    
    assert near_boundary is True
    assert disp_ci[1] == 4.0  # Clamped to supported scale max


def test_reliability_status_classification():
    estimate = AbilityEstimate(
        theta=0.42,
        initial_theta=0.0,
        iterations=5,
        converged=True,
        observed_information=12.5,
        prior_information=1.0,
        total_information=13.5,
        posterior_se=0.27,
        response_only_se=0.28,
        item_count=12
    )
    
    reliability = MeasurementUncertainty.evaluate_reliability(
        ability_estimate=estimate,
        unique_concepts_tested=6,
        total_target_concepts=7,
        target_se=0.30,
        min_items=8,
        termination_reason="target_precision_reached"
    )
    
    assert reliability.reliability_status == "reliable"
    assert reliability.concept_coverage_ratio > 0.80
    assert reliability.estimation_method == "MAP"
    assert reliability.item_bank_version == "2026.09"

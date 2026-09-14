"""
Unit Tests for Residual Memory Retention & Skill-Specific Decay Engine
"""
import pytest
from agent.psychometrics.forgetting import ForgettingEngine


def test_residual_floor_never_decays_below_pmin():
    engine = ForgettingEngine(default_decay_rate=0.10, p_min=0.15)
    initial_mastery = 0.80
    
    # Simulate 365 days of non-practice
    decayed_365 = engine.calculate_decayed_mastery(initial_mastery, elapsed_days=365.0)
    assert decayed_365 >= 0.15
    assert decayed_365 < 0.20

    # Simulate 10 years of non-practice
    decayed_3650 = engine.calculate_decayed_mastery(initial_mastery, elapsed_days=3650.0)
    assert decayed_3650 >= 0.15
    assert round(decayed_3650, 2) == 0.15


def test_initial_mastery_below_floor_unchanged():
    engine = ForgettingEngine(p_min=0.15)
    initial_mastery = 0.10
    decayed = engine.calculate_decayed_mastery(initial_mastery, elapsed_days=30.0)
    assert decayed == 0.10


def test_skill_specific_decay_rate():
    engine = ForgettingEngine(default_decay_rate=0.05)
    
    # Frequently practiced, high-accuracy skill
    lambda_practiced = engine.compute_skill_decay_rate(
        base_lambda=0.05,
        difficulty=0.2,
        practice_count=20,
        recent_accuracy=0.95
    )
    
    # Unpracticed, difficult skill with low accuracy
    lambda_unpracticed = engine.compute_skill_decay_rate(
        base_lambda=0.05,
        difficulty=0.9,
        practice_count=0,
        recent_accuracy=0.30
    )
    
    assert lambda_practiced < lambda_unpracticed
    
    # Verify retention is higher for practiced skill over 30 days
    m_practiced = engine.calculate_decayed_mastery(0.80, elapsed_days=30.0, decay_rate=lambda_practiced)
    m_unpracticed = engine.calculate_decayed_mastery(0.80, elapsed_days=30.0, decay_rate=lambda_unpracticed)
    
    assert m_practiced > m_unpracticed


def test_probability_bounds_strictly_enforced():
    engine = ForgettingEngine()
    decayed_high = engine.calculate_decayed_mastery(1.5, elapsed_days=0.0)
    decayed_low = engine.calculate_decayed_mastery(-0.5, elapsed_days=10.0)
    
    assert 0.0 <= decayed_high <= 1.0
    assert 0.0 <= decayed_low <= 1.0

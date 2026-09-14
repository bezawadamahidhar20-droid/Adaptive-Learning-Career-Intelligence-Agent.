"""
Unit Tests for Multi-Criterion CAT Stopping Engine
"""
import pytest
from agent.assessment.stopping import CATStoppingEngine


def test_stopping_enforces_minimum_items():
    engine = CATStoppingEngine(test_type="diagnostic")  # min 8, max 15, target_se 0.40, min_cov 0.60
    
    # 4 items with very low SE should NOT stop because min_items=8
    decision = engine.evaluate_stopping(
        item_count=4,
        posterior_se=0.20,
        tested_concepts_count=4,
        total_target_concepts=5
    )
    assert decision.should_stop is False
    assert decision.termination_reason == "in_progress"
    assert decision.reliability_status == "provisional"


def test_stopping_triggers_on_target_precision_and_coverage():
    engine = CATStoppingEngine(test_type="diagnostic")
    
    # 10 items, SE=0.32 (<= 0.40), coverage=4/5 (80% >= 60%), 0 critical gaps
    decision = engine.evaluate_stopping(
        item_count=10,
        posterior_se=0.32,
        tested_concepts_count=4,
        total_target_concepts=5,
        untested_critical_concepts=0
    )
    assert decision.should_stop is True
    assert decision.termination_reason == "target_precision_reached"
    assert decision.reliability_status == "reliable"


def test_stopping_prevents_early_stop_if_critical_gap_untested():
    engine = CATStoppingEngine(test_type="diagnostic")
    
    # 10 items, SE=0.32, but 1 critical gap untested
    decision = engine.evaluate_stopping(
        item_count=10,
        posterior_se=0.32,
        tested_concepts_count=4,
        total_target_concepts=5,
        untested_critical_concepts=1
    )
    assert decision.should_stop is False
    assert decision.termination_reason == "in_progress"


def test_stopping_triggers_on_max_items_reached():
    engine = CATStoppingEngine(test_type="diagnostic")  # max 15
    
    # 15 items reached but SE is still high (0.45 > 0.40)
    decision = engine.evaluate_stopping(
        item_count=15,
        posterior_se=0.45,
        tested_concepts_count=3,
        total_target_concepts=5
    )
    assert decision.should_stop is True
    assert decision.termination_reason == "max_items_reached"
    assert decision.reliability_status == "provisional"

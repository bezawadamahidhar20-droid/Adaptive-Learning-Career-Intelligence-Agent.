import pytest
import math
from agent.knowledge.irt import IRTModel

def test_irt_probability_correct():
    # When ability matches difficulty (theta = b), P = 0.50
    p = IRTModel.probability_correct(theta=0.0, a=1.0, b=0.0)
    assert abs(p - 0.50) < 1e-5

    # High ability student on easy question
    p_high = IRTModel.probability_correct(theta=2.0, a=1.5, b=-1.0)
    assert p_high > 0.95

    # Low ability student on hard question
    p_low = IRTModel.probability_correct(theta=-2.0, a=1.5, b=1.0)
    assert p_low < 0.05

def test_irt_fisher_information():
    # Fisher information maximized at theta = b
    info_match = IRTModel.fisher_information(theta=0.0, a=1.0, b=0.0)
    info_mismatch = IRTModel.fisher_information(theta=2.0, a=1.0, b=0.0)
    assert info_match == 0.25
    assert info_match > info_mismatch

def test_irt_single_step_update():
    theta = 0.0
    # Correct response increases theta
    theta_correct = IRTModel.single_step_theta_update(theta, a=1.0, b=0.0, is_correct=True)
    assert theta_correct > theta

    # Incorrect response decreases theta
    theta_incorrect = IRTModel.single_step_theta_update(theta, a=1.0, b=0.0, is_correct=False)
    assert theta_incorrect < theta

def test_irt_map_update():
    # Batch responses
    responses = [
        (1.2, -1.0, 1), # Easy correct
        (1.5, 0.0, 1),  # Medium correct
        (1.4, 1.0, 1),  # Hard correct
    ]
    updated_theta = IRTModel.update_theta_map(current_theta=0.0, responses=responses)
    assert updated_theta > 0.5

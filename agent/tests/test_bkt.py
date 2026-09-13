import pytest
from agent.knowledge.bkt import BKTKnowledgeTracer, BKTParameters

def test_bkt_parameter_validation():
    params = BKTParameters(p_init=0.2, p_transit=0.1, p_guess=0.25, p_slip=0.1)
    params.validate()

    with pytest.raises(ValueError):
        bad_params = BKTParameters(p_init=1.5)
        bad_params.validate()

def test_bkt_correct_answer_increases_mastery():
    tracer = BKTKnowledgeTracer()
    init_mastery = 0.20
    _, next_mastery = tracer.update_mastery("Python", init_mastery, is_correct=True)
    assert next_mastery > init_mastery
    assert 0.0 < next_mastery < 1.0

def test_bkt_incorrect_answer_decreases_or_damps_mastery():
    tracer = BKTKnowledgeTracer()
    init_mastery = 0.70
    p_given_obs, next_mastery = tracer.update_mastery("Python", init_mastery, is_correct=False)
    # The posterior given wrong observation should be lower than initial mastery
    assert p_given_obs < init_mastery

def test_bkt_consecutive_correct_reaches_mastery():
    tracer = BKTKnowledgeTracer()
    mastery = 0.10
    for _ in range(5):
        _, mastery = tracer.update_mastery("ML", mastery, is_correct=True)
    assert mastery > 0.85

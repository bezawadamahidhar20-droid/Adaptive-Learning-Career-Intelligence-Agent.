import pytest
from agent.agents.career_agent import CareerIntelligenceAgent

def test_explainable_career_fit():
    agent = CareerIntelligenceAgent()
    user_skills = {
        "Python": 0.85,
        "SQL": 0.70,
        "Machine Learning": 0.35,
        "Statistics": 0.45,
        "Deep Learning": 0.20
    }
    fit = agent.evaluate_career_fit("data_scientist", user_skills)
    
    assert fit.role_id == "data_scientist"
    assert fit.suitability_score > 0.0
    assert "Python" in str(fit.strengths)
    assert len(fit.missing_skills) > 0
    assert "Recommended" in fit.explanation or "because" in fit.explanation
    assert len(fit.priority_skills_to_learn) > 0

def test_compare_all_roles():
    agent = CareerIntelligenceAgent()
    user_skills = {"SQL": 0.85, "Python": 0.75, "Statistics": 0.75, "Machine Learning": 0.60}
    fits = agent.evaluate_all_roles(user_skills)
    
    assert len(fits) >= 3
    # With high SQL and Stats, Data Analyst should be top recommendation
    assert fits[0].role_id == "data_analyst"
    assert fits[0].is_job_ready is True

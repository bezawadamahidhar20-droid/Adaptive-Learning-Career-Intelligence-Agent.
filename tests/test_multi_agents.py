import pytest
from agent.agent import AdaptiveLearningAgent

def test_multi_agent_orchestration_pipeline():
    agent = AdaptiveLearningAgent()
    
    # 1. Profile Analyzer
    profile_res = agent.profile_analyzer.analyze_profile(
        user_id="u123",
        profile_data={"graduation_year": 2026, "target_role": "data_scientist", "experience_level": "Student"}
    )
    assert profile_res.urgency_tier in ["high", "moderate", "planning"]

    # 2. Skill Analyzer with descriptive levels
    raw_skills = [
        {"name": "Python", "level": "Good"},
        {"name": "SQL", "level": "Average"},
        {"name": "Machine Learning", "level": "Below Average"},
        {"name": "Statistics", "level": "Average"},
        {"name": "Deep Learning", "level": "Below Average"}
    ]
    standardized = agent.skill_analyzer.standardize_and_rank_skills(raw_skills)
    assert len(standardized) == 5

    # 3. Career Agent
    skill_dict = {s.skill_name: s.numeric_mastery for s in standardized}
    fit = agent.career_agent.evaluate_career_fit("data_scientist", skill_dict)
    assert fit.role_id == "data_scientist"
    assert isinstance(fit.suitability_score, float)

    # 4. Roadmap Agent
    roadmap = agent.roadmap_agent.generate_adaptive_roadmap("data_scientist", skill_dict)
    assert len(roadmap) > 0

    # 5. Placement Agent
    placement = agent.placement_agent.get_placement_modules("data_scientist")
    assert len(placement) == 4

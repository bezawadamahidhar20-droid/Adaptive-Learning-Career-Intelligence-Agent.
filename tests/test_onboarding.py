import pytest
from agent.agents.skill_analyzer import SkillAnalyzerAgent
from agent.agents.roadmap_agent import RoadmapAgent
from backend.database import get_db_connection, init_db

def setup_module():
    init_db()

def test_onboarding_skill_standardization():
    agent = SkillAnalyzerAgent()
    raw_skills = [
        {"name": "Python", "level": "Good"},
        {"name": "SQL", "level": "Average"},
        {"name": "Machine Learning", "level": "Below Average"}
    ]
    standardized = agent.standardize_and_rank_skills(raw_skills, role_weights={"Machine Learning": 0.27, "Python": 0.25, "SQL": 0.18})
    
    assert len(standardized) == 3
    # Machine Learning has high gap (0.27 * (1 - 0.25) = 0.2025) and should be priority #1
    assert standardized[0].skill_name == "Machine Learning"
    assert standardized[0].descriptive_level == "Below Average"
    assert standardized[0].priority_rank == 1

def test_onboarding_roadmap_initialization():
    roadmap_agent = RoadmapAgent()
    skills = {"Python": 0.75, "SQL": 0.50, "Machine Learning": 0.25}
    tasks = roadmap_agent.generate_adaptive_roadmap("data_scientist", skills)
    
    assert len(tasks) > 5
    stages = set(t.stage_name for t in tasks)
    assert any("Foundations" in s for s in stages)
    assert any("Portfolio" in s or "Projects" in s for s in stages)
    assert any("Placement" in s for s in stages)

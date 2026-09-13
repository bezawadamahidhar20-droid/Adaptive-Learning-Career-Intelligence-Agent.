import pytest
from agent.agents.roadmap_agent import RoadmapAgent
from agent.agents.adaptation_agent import AdaptationAgent

def test_roadmap_adaptation_on_skill_improvement():
    roadmap_agent = RoadmapAgent()
    adaptation_agent = AdaptationAgent(roadmap_agent=roadmap_agent)

    initial_skills = {
        "Python": 0.25,
        "SQL": 0.25,
        "Machine Learning": 0.25,
        "Statistics": 0.25,
        "Deep Learning": 0.25
    }
    initial_tasks = roadmap_agent.generate_adaptive_roadmap("data_scientist", initial_skills)
    
    # Verify early stage tasks not auto-completed
    stage1_py = next(t for t in initial_tasks if t.id == "DS_S1_01")
    assert stage1_py.is_completed is False

    # Simulate mastery gain in Python to 0.90
    updated_skills = {
        "Python": 0.90,
        "SQL": 0.25,
        "Machine Learning": 0.25,
        "Statistics": 0.25,
        "Deep Learning": 0.25
    }
    adapted_report = adaptation_agent.process_adaptation(
        user_id="u1",
        target_role="data_scientist",
        previous_readiness=25.0,
        current_skill_masteries=updated_skills
    )

    assert adapted_report.updated_readiness > adapted_report.previous_readiness
    assert adapted_report.readiness_delta > 0
    # The foundation task for mastered Python is now marked completed
    adapted_py = next(t for t in adapted_report.adapted_roadmap if t.id == "DS_S1_01")
    assert adapted_py.is_completed is True

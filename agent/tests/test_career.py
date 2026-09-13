import pytest
from agent.career.role_matcher import RoleMatcher, RoleProfile
from agent.career.skill_gap import SkillGapAnalyzer

def test_career_readiness_calculation():
    matcher = RoleMatcher()
    sample_skills = {
        "Python": 0.80,
        "SQL": 0.70,
        "Machine Learning": 0.40,
        "Statistics": 0.50,
        "Deep Learning": 0.20
    }
    readiness = matcher.calculate_readiness("data_scientist", sample_skills)
    assert 50.0 <= readiness <= 70.0

def test_skill_gap_ranking_and_priorities():
    analyzer = SkillGapAnalyzer()
    sample_skills = {
        "Python": 0.80,
        "SQL": 0.70,
        "Machine Learning": 0.30,
        "Statistics": 0.40,
        "Deep Learning": 0.10
    }
    report = analyzer.analyze_gaps("data_scientist", sample_skills)
    
    assert report.role_id == "data_scientist"
    assert report.is_job_ready is False
    assert len(report.gaps) == 5
    # Machine Learning and Deep Learning should be top gap priorities
    top_gap_skills = [report.gaps[0].skill, report.gaps[1].skill]
    assert "Machine Learning" in top_gap_skills or "Deep Learning" in top_gap_skills

"""
Career Intelligence Router
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict
from ..schemas import RoleInfo, CareerAnalysisResponse, SkillGapItemResponse
from agent.career.role_matcher import ROLE_REGISTRY, RoleMatcher
from agent.career.skill_gap import SkillGapAnalyzer
from ..database import get_db_connection

router = APIRouter(prefix="/career", tags=["career"])
role_matcher = RoleMatcher()
skill_gap_analyzer = SkillGapAnalyzer(role_matcher)

@router.get("/roles", response_model=List[RoleInfo])
def get_roles():
    roles = role_matcher.list_roles()
    return [
        RoleInfo(
            role_id=r.role_id,
            title=r.title,
            description=r.description,
            skill_weights=r.skill_weights,
            target_thresholds=r.target_thresholds
        ) for r in roles
    ]

@router.get("/analyze/{user_id}/{role_id}", response_model=CareerAnalysisResponse)
def analyze_user_career(user_id: str, role_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Load student's skill masteries from knowledge_states
    cursor.execute("SELECT concept, skill, mastery FROM knowledge_states WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    skill_masteries: Dict[str, float] = {}
    if rows:
        skill_counts: Dict[str, int] = {}
        for r in rows:
            skill = r["skill"] or "General"
            skill_masteries[skill] = skill_masteries.get(skill, 0.0) + r["mastery"]
            skill_counts[skill] = skill_counts.get(skill, 0) + 1
        for s in skill_masteries:
            skill_masteries[s] = round(skill_masteries[s] / skill_counts[s], 4)

    try:
        report = skill_gap_analyzer.analyze_gaps(role_id, skill_masteries)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    gaps_response = [
        SkillGapItemResponse(
            skill=g.skill,
            current_mastery=g.current_mastery,
            target_threshold=g.target_threshold,
            importance_weight=g.importance_weight,
            gap_magnitude=g.gap_magnitude,
            priority_rank=g.priority_rank,
            estimated_questions_to_mastery=g.estimated_questions_to_mastery,
            recommendation_text=g.recommendation_text
        ) for g in report.gaps
    ]

    return CareerAnalysisResponse(
        role_id=report.role_id,
        role_title=report.role_title,
        readiness_score=report.readiness_score,
        is_job_ready=report.is_job_ready,
        top_priority_skill=report.top_priority_skill,
        gaps=gaps_response,
        estimated_study_hours=report.estimated_study_hours
    )

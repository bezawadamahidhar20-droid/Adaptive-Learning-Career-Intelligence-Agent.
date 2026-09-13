"""
Explainable Career Intelligence Router
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from ..schemas import RoleInfo, ExplainableCareerFitResponse
from ..database import get_db_connection
from ..security import get_current_user
from agent.agent import AdaptiveLearningAgent
from agent.career.role_matcher import ROLE_REGISTRY

router = APIRouter(prefix="/career", tags=["career"])
agent = AdaptiveLearningAgent()

@router.get("/roles", response_model=List[RoleInfo])
def get_roles():
    """Lists all available industry career target tracks."""
    roles = agent.role_matcher.list_roles()
    return [
        RoleInfo(
            role_id=r.role_id,
            title=r.title,
            description=r.description,
            skill_weights=r.skill_weights,
            target_thresholds=r.target_thresholds
        ) for r in roles
    ]

@router.get("/fit", response_model=ExplainableCareerFitResponse)
def get_career_fit(current_user: dict = Depends(get_current_user)):
    """Returns explainable suitability analysis for the authenticated user's target role."""
    user_id = current_user["id"]
    target_role = current_user["target_role"] or "data_scientist"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT skill_name, numeric_mastery FROM user_skills WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    skill_dict = {r["skill_name"]: r["numeric_mastery"] for r in rows}
    fit = agent.career_agent.evaluate_career_fit(target_role, skill_dict)

    return ExplainableCareerFitResponse(
        role_id=fit.role_id,
        role_title=fit.role_title,
        suitability_score=fit.suitability_score,
        is_recommended=fit.is_recommended,
        is_job_ready=fit.is_job_ready,
        explanation=fit.explanation,
        strengths=fit.strengths,
        missing_skills=fit.missing_skills,
        priority_skills_to_learn=fit.priority_skills_to_learn
    )

@router.get("/compare", response_model=List[ExplainableCareerFitResponse])
def compare_all_roles(current_user: dict = Depends(get_current_user)):
    """Compares student skills across all industry tracks and ranks by explainable suitability."""
    user_id = current_user["id"]
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT skill_name, numeric_mastery FROM user_skills WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    skill_dict = {r["skill_name"]: r["numeric_mastery"] for r in rows}
    all_fits = agent.career_agent.evaluate_all_roles(skill_dict)

    return [
        ExplainableCareerFitResponse(
            role_id=fit.role_id,
            role_title=fit.role_title,
            suitability_score=fit.suitability_score,
            is_recommended=fit.is_recommended,
            is_job_ready=fit.is_job_ready,
            explanation=fit.explanation,
            strengths=fit.strengths,
            missing_skills=fit.missing_skills,
            priority_skills_to_learn=fit.priority_skills_to_learn
        ) for fit in all_fits
    ]

@router.post("/set-target")
def set_target_role(role_id: str, current_user: dict = Depends(get_current_user)):
    """Switches the student's target career role."""
    if role_id not in ROLE_REGISTRY:
        raise HTTPException(status_code=400, detail=f"Invalid target role: {role_id}")

    user_id = current_user["id"]
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET target_role = ? WHERE id = ?", (role_id, user_id))
    conn.commit()
    conn.close()

    return {"status": "success", "target_role": role_id}

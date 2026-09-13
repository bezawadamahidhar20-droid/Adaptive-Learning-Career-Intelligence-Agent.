"""
Student Dashboard Aggregator Router
Aggregates authentic, real-time data from database and multi-agent systems.
Eliminates all fake/mock progress metrics.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Optional
from ..schemas import (
    DashboardSummaryResponse, SkillItemResponse,
    ExplainableCareerFitResponse, RoadmapTaskResponse,
    AssessmentQuestionResponse
)
from ..database import get_db_connection
from ..security import get_current_user
from .assessment import _load_student_state, agent
from agent.agents.skill_analyzer import numeric_to_descriptive

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/", response_model=DashboardSummaryResponse)
def get_dashboard_summary(current_user: dict = Depends(get_current_user)):
    """Returns the authenticated user's real-time dashboard data."""
    user_id = current_user["id"]
    target_role = current_user["target_role"] or "data_scientist"
    role_obj = agent.role_matcher.get_role(target_role) or agent.role_matcher.get_role("data_scientist")

    # Load real student state from SQLite
    student_state = _load_student_state(user_id)
    total_attempts = student_state["total_attempts"]
    correct_attempts = student_state["correct_attempts"]
    has_sufficient_data = total_attempts > 0

    # Load user skills
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT skill_name, category, descriptive_level, numeric_mastery,
           importance_weight, target_level, confidence, evidence_source,
           improvement_recommendation
    FROM user_skills WHERE user_id = ?
    ORDER BY (importance_weight * (1.0 - numeric_mastery)) DESC
    """, (user_id,))
    skill_rows = cursor.fetchall()

    # Load roadmap tasks preview
    cursor.execute("""
    SELECT id, target_role, stage_name, title, description, category, associated_skill, priority_rank, is_completed
    FROM roadmap_tasks WHERE user_id = ? AND is_completed = 0
    ORDER BY priority_rank ASC LIMIT 3
    """, (user_id,))
    roadmap_rows = cursor.fetchall()
    conn.close()

    # Construct skill items
    skill_items: List[SkillItemResponse] = []
    skill_dict: Dict[str, float] = {}
    for idx, r in enumerate(skill_rows, 1):
        skill_dict[r["skill_name"]] = r["numeric_mastery"]
        desc_level = r["descriptive_level"] or numeric_to_descriptive(r["numeric_mastery"])
        skill_items.append(SkillItemResponse(
            skill_name=r["skill_name"],
            category=r["category"],
            descriptive_level=desc_level,
            numeric_mastery=r["numeric_mastery"],
            importance_weight=r["importance_weight"],
            target_level=r["target_level"],
            confidence=r["confidence"],
            evidence_source=r["evidence_source"],
            improvement_recommendation=r["improvement_recommendation"] or f"Continue adaptive practice in {r['skill_name']}.",
            priority_rank=idx
        ))

    # Evaluate explainable career fit
    fit = agent.career_agent.evaluate_career_fit(target_role, skill_dict)
    career_fit_response = ExplainableCareerFitResponse(
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

    # Roadmap preview
    roadmap_preview: List[RoadmapTaskResponse] = [
        RoadmapTaskResponse(
            id=r["id"],
            target_role=r["target_role"],
            stage_name=r["stage_name"],
            title=r["title"],
            description=r["description"],
            category=r["category"],
            associated_skill=r["associated_skill"],
            priority_rank=r["priority_rank"],
            is_completed=bool(r["is_completed"])
        ) for r in roadmap_rows
    ]

    # Next recommended adaptive assignment
    next_preview_raw = agent.generate_assignment(student_state, total_questions=3, target_role=target_role)
    next_preview = [
        AssessmentQuestionResponse(
            id=q["id"],
            skill=q.get("skill", "General"),
            concept=q.get("concept", "General"),
            subtopic=q.get("subtopic", ""),
            difficulty=q.get("difficulty", 3),
            question=q.get("question", ""),
            options=q.get("options", []),
            selection_reason=q.get("selection_reason", ""),
            selection_score=q.get("selection_score", 0.0)
        ) for q in next_preview_raw
    ]

    accuracy = round((correct_attempts / max(1, total_attempts)) * 100, 1) if has_sufficient_data else 0.0
    top_priority = fit.priority_skills_to_learn[0] if fit.priority_skills_to_learn else None

    return DashboardSummaryResponse(
        user_id=user_id,
        name=current_user["name"],
        target_role=target_role,
        role_title=role_obj.title,
        onboarding_completed=current_user["onboarding_completed"],
        theta=student_state["theta"] if has_sufficient_data else 0.0,
        total_attempts=total_attempts,
        correct_attempts=correct_attempts,
        accuracy_percentage=accuracy,
        career_readiness=fit.suitability_score,
        is_job_ready=fit.is_job_ready,
        top_priority_skill=top_priority,
        skills=skill_items,
        career_fit=career_fit_response,
        roadmap_preview=roadmap_preview,
        next_recommended_assignment=next_preview,
        has_sufficient_data=has_sufficient_data
    )

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

    # Load recent assessment history with reliability metrics
    cursor.execute("""
    SELECT a.id, a.target_role, a.total_questions, a.score_percentage, a.correct_answers, a.estimated_theta, a.created_at,
           r.reliability_status, r.posterior_se, r.display_ci_low, r.display_ci_high
    FROM assessments a
    LEFT JOIN assessment_reliability r ON a.id = r.assessment_id
    WHERE a.user_id = ?
    ORDER BY a.created_at DESC LIMIT 10
    """, (user_id,))
    assessment_rows = cursor.fetchall()

    # Load latest reliability record
    cursor.execute("""
    SELECT * FROM assessment_reliability WHERE user_id = ? ORDER BY created_at DESC LIMIT 1
    """, (user_id,))
    latest_rel_row = cursor.fetchone()
    conn.close()

    # Construct skill items
    skill_items: List[SkillItemResponse] = []
    skill_dict: Dict[str, float] = {}
    strongest_skills: List[str] = []
    weakest_skills: List[str] = []

    for idx, r in enumerate(skill_rows, 1):
        m_val = r["numeric_mastery"]
        s_name = r["skill_name"]
        skill_dict[s_name] = m_val
        desc_level = r["descriptive_level"] or numeric_to_descriptive(m_val)
        
        if m_val >= 0.65:
            strongest_skills.append(s_name)
        elif m_val < 0.50:
            weakest_skills.append(s_name)

        skill_items.append(SkillItemResponse(
            skill_name=s_name,
            category=r["category"],
            descriptive_level=desc_level,
            numeric_mastery=m_val,
            importance_weight=r["importance_weight"],
            target_level=r["target_level"],
            confidence=r["confidence"],
            evidence_source=r["evidence_source"],
            improvement_recommendation=r["improvement_recommendation"] or f"Continue adaptive practice in {s_name}.",
            priority_rank=idx
        ))

    overall_mastery = round(sum(skill_dict.values()) / max(1, len(skill_dict)) * 100.0, 1) if skill_dict else 0.0

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

    # Assessment history
    from ..schemas import AssessmentHistoryItem, AssessmentReliabilityResponse
    assessment_history = [
        AssessmentHistoryItem(
            id=r["id"],
            target_role=r["target_role"],
            total_questions=r["total_questions"],
            score_percentage=r["score_percentage"],
            correct_answers=r["correct_answers"] if "correct_answers" in r.keys() else 0,
            estimated_theta=round(r["estimated_theta"], 2) if ("estimated_theta" in r.keys() and r["estimated_theta"] is not None) else 0.0,
            reliability_status=r["reliability_status"] if ("reliability_status" in r.keys() and r["reliability_status"]) else "provisional",
            posterior_se=round(r["posterior_se"], 2) if ("posterior_se" in r.keys() and r["posterior_se"] is not None) else None,
            display_interval=[r["display_ci_low"], r["display_ci_high"]] if ("display_ci_low" in r.keys() and r["display_ci_low"] is not None) else None,
            created_at=str(r["created_at"])
        ) for r in assessment_rows
    ]

    # Latest reliability object
    latest_rel_obj = None
    if latest_rel_row:
        raw_ci = [latest_rel_row["raw_ci_low"], latest_rel_row["raw_ci_high"]]
        disp_ci = [latest_rel_row["display_ci_low"], latest_rel_row["display_ci_high"]]
        latest_rel_obj = AssessmentReliabilityResponse(
            theta=latest_rel_row["theta"],
            posterior_standard_error=latest_rel_row["posterior_se"],
            response_only_standard_error=latest_rel_row["response_only_se"],
            observed_information=latest_rel_row["observed_info"],
            prior_information=latest_rel_row["prior_info"],
            raw_interval=raw_ci,
            display_interval=disp_ci,
            scale_bounds=[-4.0, 4.0],
            near_boundary_warning=(latest_rel_row["theta"] <= -3.5 or latest_rel_row["theta"] >= 3.5),
            boundary_message=None,
            item_count=latest_rel_row["item_count"],
            concept_count=latest_rel_row["concept_count"],
            concept_coverage_ratio=latest_rel_row["concept_coverage_ratio"],
            reliability_status=latest_rel_row["reliability_status"],
            termination_reason=latest_rel_row["termination_reason"],
            estimation_method=latest_rel_row["estimation_method"],
            item_bank_version=latest_rel_row["item_bank_version"]
        )

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
    top_priority = fit.priority_skills_to_learn[0] if fit.priority_skills_to_learn else (weakest_skills[0] if weakest_skills else None)
    
    if top_priority:
        recommended_action = f"Complete an adaptive CAT session on '{top_priority}' to target your highest-weight gap."
    else:
        recommended_action = "Maintain mastery across core competencies with spaced repetition review."

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
        overall_mastery=overall_mastery,
        career_readiness=fit.suitability_score,
        is_job_ready=fit.is_job_ready,
        top_priority_skill=top_priority,
        strongest_skills=strongest_skills,
        weakest_skills=weakest_skills,
        recommended_next_action=recommended_action,
        skills=skill_items,
        career_fit=career_fit_response,
        roadmap_preview=roadmap_preview,
        next_recommended_assignment=next_preview,
        assessment_history=assessment_history,
        latest_reliability=latest_rel_obj,
        has_sufficient_data=has_sufficient_data
    )

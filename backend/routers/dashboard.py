"""
Student Dashboard Aggregator Router
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, List
from ..schemas import DashboardSummaryResponse, SkillGapItemResponse, AssessmentQuestionResponse
from ..database import get_db_connection
from .assessment import _load_student_state, agent
from .career import skill_gap_analyzer, role_matcher

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/{user_id}", response_model=DashboardSummaryResponse)
def get_dashboard_data(user_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT name, email, target_role FROM users WHERE id = ?", (user_id,))
    user_row = cursor.fetchone()
    conn.close()

    if not user_row:
        raise HTTPException(status_code=404, detail="User not found")

    target_role = user_row["target_role"] or "data_scientist"
    role_obj = role_matcher.get_role(target_role) or role_matcher.get_role("data_scientist")

    # Load current student profile
    student_state = _load_student_state(user_id)
    
    # Analyze career fit
    report = skill_gap_analyzer.analyze_gaps(target_role, student_state["skill_mastery"])

    # Generate next preview assignment (3 questions)
    next_preview_raw = agent.generate_assignment(student_state, total_questions=3, target_role=target_role)
    next_preview = [
        AssessmentQuestionResponse(
            id=q["id"],
            skill=q.get("skill", "General"),
            concept=q.get("concept", "General"),
            subtopic=q.get("subtopic", ""),
            difficulty=q.get("difficulty", 3),
            question=q.get("question", ""),
            options=q.get("options", [])
        ) for q in next_preview_raw
    ]

    total_attempts = student_state["total_attempts"]
    correct_attempts = student_state["correct_attempts"]
    accuracy = round((correct_attempts / max(1, total_attempts)) * 100, 1) if total_attempts > 0 else 0.0

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

    return DashboardSummaryResponse(
        user_id=user_id,
        name=user_row["name"],
        target_role=target_role,
        role_title=role_obj.title,
        theta=student_state["theta"],
        total_attempts=total_attempts,
        correct_attempts=correct_attempts,
        accuracy_percentage=accuracy,
        career_readiness=report.readiness_score,
        is_job_ready=report.is_job_ready,
        top_priority_skill=report.top_priority_skill,
        skill_masteries=student_state["skill_mastery"],
        concept_masteries=student_state["concept_mastery"],
        gaps=gaps_response,
        next_recommended_assignment=next_preview
    )

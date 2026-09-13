"""
Onboarding Router
Handles mandatory post-first-login profile onboarding:
Collects education background, technical skills with descriptive levels, soft skills,
and career goals; initializes user skills and adaptive roadmap.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any
from ..database import get_db_connection
from ..security import get_current_user
from ..schemas import OnboardingSubmitRequest, OnboardingStatusResponse
from agent.agent import AdaptiveLearningAgent
from agent.career.role_matcher import ROLE_REGISTRY

router = APIRouter(prefix="/onboarding", tags=["onboarding"])
agent = AdaptiveLearningAgent()

@router.get("/status", response_model=OnboardingStatusResponse)
def check_onboarding_status(current_user: dict = Depends(get_current_user)):
    """Checks whether the authenticated user has completed mandatory onboarding."""
    user_id = current_user["id"]
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT education_level, major, graduation_year, experience_level, placement_goal, preferred_technologies, soft_skills
    FROM student_profiles WHERE user_id = ?
    """, (user_id,))
    profile_row = cursor.fetchone()
    conn.close()

    profile_dict = None
    if profile_row:
        profile_dict = {
            "education_level": profile_row["education_level"],
            "major": profile_row["major"],
            "graduation_year": profile_row["graduation_year"],
            "experience_level": profile_row["experience_level"],
            "placement_goal": profile_row["placement_goal"],
            "preferred_technologies": profile_row["preferred_technologies"],
            "soft_skills": profile_row["soft_skills"]
        }

    return OnboardingStatusResponse(
        onboarding_completed=current_user["onboarding_completed"],
        user_id=user_id,
        profile=profile_dict
    )

@router.post("/submit")
def submit_onboarding(payload: OnboardingSubmitRequest, current_user: dict = Depends(get_current_user)):
    """
    Submits student profile and skill self-ratings, standardizes skills via SkillAnalyzerAgent,
    persists records to database, and initializes the adaptive roadmap.
    """
    user_id = current_user["id"]
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Update target role & mark onboarding complete on users table
    cursor.execute(
        "UPDATE users SET target_role = ?, onboarding_completed = 1 WHERE id = ?",
        (payload.target_role, user_id)
    )

    # 2. Persist extended profile info
    tech_str = ", ".join(payload.preferred_technologies)
    soft_str = ", ".join(payload.soft_skills)
    
    cursor.execute("""
    INSERT INTO student_profiles (
        user_id, education_level, major, graduation_year, experience_level,
        placement_goal, preferred_technologies, soft_skills, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(user_id) DO UPDATE SET
        education_level = excluded.education_level,
        major = excluded.major,
        graduation_year = excluded.graduation_year,
        experience_level = excluded.experience_level,
        placement_goal = excluded.placement_goal,
        preferred_technologies = excluded.preferred_technologies,
        soft_skills = excluded.soft_skills,
        updated_at = CURRENT_TIMESTAMP
    """, (
        user_id, payload.education_level, payload.major, payload.graduation_year,
        payload.experience_level, payload.placement_goal, tech_str, soft_str
    ))

    # 3. Standardize and insert technical skills
    role_obj = agent.role_matcher.get_role(payload.target_role) or agent.role_matcher.get_role("data_scientist")
    raw_skills = [{"skill_name": s.name, "category": s.category, "descriptive_level": s.level} for s in payload.technical_skills]
    
    standardized_skills = agent.skill_analyzer.standardize_and_rank_skills(
        raw_skills=raw_skills,
        role_weights=role_obj.skill_weights
    )

    skill_masteries_dict = {}
    for skill in standardized_skills:
        skill_masteries_dict[skill.skill_name] = skill.numeric_mastery
        cursor.execute("""
        INSERT INTO user_skills (
            user_id, skill_name, category, descriptive_level, numeric_mastery,
            importance_weight, target_level, confidence, evidence_source,
            improvement_recommendation, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id, skill_name) DO UPDATE SET
            category = excluded.category,
            descriptive_level = excluded.descriptive_level,
            numeric_mastery = excluded.numeric_mastery,
            importance_weight = excluded.importance_weight,
            target_level = excluded.target_level,
            confidence = excluded.confidence,
            improvement_recommendation = excluded.improvement_recommendation,
            updated_at = CURRENT_TIMESTAMP
        """, (
            user_id, skill.skill_name, skill.category, skill.descriptive_level,
            skill.numeric_mastery, skill.importance_weight, skill.target_level,
            skill.confidence, skill.evidence_source, skill.improvement_recommendation
        ))

    # 4. Generate & persist initial adaptive roadmap tasks
    roadmap_tasks = agent.roadmap_agent.generate_adaptive_roadmap(
        target_role=payload.target_role,
        user_skills=skill_masteries_dict
    )

    for task in roadmap_tasks:
        cursor.execute("""
        INSERT INTO roadmap_tasks (
            id, user_id, target_role, stage_name, title, description, category, associated_skill, priority_rank, is_completed
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO NOTHING
        """, (
            f"{user_id}_{task.id}", user_id, payload.target_role, task.stage_name,
            task.title, task.description, task.category, task.associated_skill,
            task.priority_rank, 1 if task.is_completed else 0
        ))

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "message": "Onboarding completed successfully. Profile, skills, and adaptive roadmap initialized.",
        "user_id": user_id,
        "target_role": payload.target_role,
        "skills_registered": len(standardized_skills),
        "roadmap_tasks_initialized": len(roadmap_tasks)
    }

"""
Skill Intelligence Router
Provides categorized skill catalog with descriptive levels ('Below Average', 'Average', 'Good', 'Perfect'),
importance weights, priority ranks, confidence, and actionable recommendations.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from ..database import get_db_connection
from ..security import get_current_user
from ..schemas import SkillItemResponse
from agent.agents.skill_analyzer import numeric_to_descriptive

router = APIRouter(prefix="/skills", tags=["skills"])

@router.get("/", response_model=List[SkillItemResponse])
def get_user_skills(current_user: dict = Depends(get_current_user)):
    """Returns the authenticated user's prioritized skill profile."""
    user_id = current_user["id"]
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT skill_name, category, descriptive_level, numeric_mastery,
           importance_weight, target_level, confidence, evidence_source,
           improvement_recommendation
    FROM user_skills WHERE user_id = ?
    ORDER BY (importance_weight * (1.0 - numeric_mastery)) DESC
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()

    results = []
    for idx, r in enumerate(rows, 1):
        desc_level = r["descriptive_level"] or numeric_to_descriptive(r["numeric_mastery"])
        results.append(SkillItemResponse(
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

    return results

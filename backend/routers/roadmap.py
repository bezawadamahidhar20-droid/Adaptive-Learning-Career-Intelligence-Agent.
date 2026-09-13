"""
Dynamic Adaptive Roadmap Router
Manages multi-stage personalized learning roadmap tasks, practical projects, and task completion tracking.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List
from ..database import get_db_connection
from ..security import get_current_user
from ..schemas import RoadmapSummaryResponse, RoadmapTaskResponse, TaskToggleRequest
from agent.agent import AdaptiveLearningAgent

router = APIRouter(prefix="/roadmap", tags=["roadmap"])
agent = AdaptiveLearningAgent()

@router.get("/", response_model=RoadmapSummaryResponse)
def get_user_roadmap(current_user: dict = Depends(get_current_user)):
    """Returns the authenticated user's adaptive roadmap grouped by milestone stages."""
    user_id = current_user["id"]
    target_role = current_user["target_role"] or "data_scientist"

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, target_role, stage_name, title, description, category, associated_skill, priority_rank, is_completed
    FROM roadmap_tasks WHERE user_id = ?
    ORDER BY priority_rank ASC, id ASC
    """, (user_id,))
    rows = cursor.fetchall()

    # If no roadmap exists yet, generate initial one
    if not rows:
        cursor.execute("SELECT skill_name, numeric_mastery FROM user_skills WHERE user_id = ?", (user_id,))
        s_rows = cursor.fetchall()
        user_skills = {r["skill_name"]: r["numeric_mastery"] for r in s_rows}
        
        generated_tasks = agent.roadmap_agent.generate_adaptive_roadmap(target_role, user_skills)
        for task in generated_tasks:
            cursor.execute("""
            INSERT INTO roadmap_tasks (
                id, user_id, target_role, stage_name, title, description, category, associated_skill, priority_rank, is_completed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO NOTHING
            """, (
                f"{user_id}_{task.id}", user_id, target_role, task.stage_name,
                task.title, task.description, task.category, task.associated_skill,
                task.priority_rank, 1 if task.is_completed else 0
            ))
        conn.commit()

        cursor.execute("""
        SELECT id, target_role, stage_name, title, description, category, associated_skill, priority_rank, is_completed
        FROM roadmap_tasks WHERE user_id = ?
        ORDER BY priority_rank ASC, id ASC
        """, (user_id,))
        rows = cursor.fetchall()

    conn.close()

    stages_dict: Dict[str, List[RoadmapTaskResponse]] = {}
    total_tasks = len(rows)
    completed_tasks = 0

    for r in rows:
        is_comp = bool(r["is_completed"])
        if is_comp:
            completed_tasks += 1

        stage = r["stage_name"]
        if stage not in stages_dict:
            stages_dict[stage] = []

        stages_dict[stage].append(RoadmapTaskResponse(
            id=r["id"],
            target_role=r["target_role"],
            stage_name=r["stage_name"],
            title=r["title"],
            description=r["description"],
            category=r["category"],
            associated_skill=r["associated_skill"],
            priority_rank=r["priority_rank"],
            is_completed=is_comp
        ))

    pct = round((completed_tasks / max(1, total_tasks)) * 100, 1)
    return RoadmapSummaryResponse(
        target_role=target_role,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        completion_percentage=pct,
        stages=stages_dict
    )

@router.post("/toggle-task")
def toggle_roadmap_task(payload: TaskToggleRequest, current_user: dict = Depends(get_current_user)):
    """Toggles task completion state for the authenticated user."""
    user_id = current_user["id"]
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE roadmap_tasks
    SET is_completed = ?, completed_at = CURRENT_TIMESTAMP
    WHERE id = ? AND user_id = ?
    """, (1 if payload.is_completed else 0, payload.task_id, user_id))

    conn.commit()
    conn.close()

    return {"status": "success", "task_id": payload.task_id, "is_completed": payload.is_completed}

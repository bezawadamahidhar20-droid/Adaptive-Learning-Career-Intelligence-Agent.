"""
Placement Preparation Router
Provides role-specific placement preparation hubs:
1. Technical Coding & DSA Challenge Bank
2. Quantitative & Logical Aptitude Practice
3. Technical & Behavioral / HR Interview Question Bank with Model Answers
4. Portfolio, GitHub & Resume Checklists
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from ..database import get_db_connection
from ..security import get_current_user
from ..schemas import PlacementModuleResponse, PlacementProgressToggleRequest
from agent.agent import AdaptiveLearningAgent

router = APIRouter(prefix="/placement", tags=["placement"])
agent = AdaptiveLearningAgent()

@router.get("/modules", response_model=List[PlacementModuleResponse])
def get_placement_modules(current_user: dict = Depends(get_current_user)):
    """Returns tailored placement preparation modules for authenticated user's target role."""
    target_role = current_user["target_role"] or "data_scientist"
    user_id = current_user["id"]

    modules = agent.placement_agent.get_placement_modules(target_role)

    # Fetch user's saved placement progress
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT module_type, item_id, status FROM placement_progress WHERE user_id = ?", (user_id,))
    progress_rows = cursor.fetchall()
    conn.close()

    progress_map = {(r["module_type"], r["item_id"]): r["status"] for r in progress_rows}

    response_list = []
    for mod in modules:
        augmented_items = []
        for item in mod.items:
            item_copy = item.copy()
            item_id = item.get("id", "")
            item_copy["user_status"] = progress_map.get((mod.module_type, item_id), "pending")
            augmented_items.append(item_copy)

        response_list.append(PlacementModuleResponse(
            module_type=mod.module_type,
            title=mod.title,
            description=mod.description,
            items=augmented_items
        ))

    return response_list

@router.post("/toggle-item")
def toggle_placement_item(payload: PlacementProgressToggleRequest, current_user: dict = Depends(get_current_user)):
    """Saves progress on a placement challenge or checklist item."""
    user_id = current_user["id"]
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO placement_progress (user_id, module_type, item_id, title, status, updated_at)
    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(user_id, module_type, item_id) DO UPDATE SET
        status = excluded.status,
        updated_at = CURRENT_TIMESTAMP
    """, (user_id, payload.module_type, payload.item_id, payload.item_id, payload.status))

    conn.commit()
    conn.close()

    return {"status": "success", "item_id": payload.item_id, "new_status": payload.status}

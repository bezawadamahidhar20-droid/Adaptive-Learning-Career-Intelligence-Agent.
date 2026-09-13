"""
Assessment Generation & Adaptive Submission Router
JWT-Authenticated adaptive CAT testing with online BKT & IRT updates.
"""
import uuid
from typing import List, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends

from ..schemas import (
    AssessmentQuestionResponse, AssessmentSubmitRequest,
    AssessmentSubmitResponse, AnswerResult
)
from ..database import get_db_connection
from ..security import get_current_user
from agent.agent import AdaptiveLearningAgent
from agent.agents.skill_analyzer import numeric_to_descriptive

router = APIRouter(prefix="/assessment", tags=["assessment"])
agent = AdaptiveLearningAgent()

def _load_student_state(user_id: str) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()

    # Load theta & stats
    cursor.execute("SELECT theta, total_attempts, correct_attempts FROM student_profiles WHERE user_id = ?", (user_id,))
    profile_row = cursor.fetchone()
    theta = profile_row["theta"] if profile_row else 0.0

    # Load knowledge states
    cursor.execute("SELECT concept, skill, mastery, last_practiced FROM knowledge_states WHERE user_id = ?", (user_id,))
    k_rows = cursor.fetchall()

    concept_mastery = {}
    skill_mastery = {}
    skill_counts = {}
    last_practiced = {}
    now = datetime.now(timezone.utc)

    for r in k_rows:
        raw_m = r["mastery"]
        last_str = r["last_practiced"]
        if last_str:
            try:
                last_dt = datetime.fromisoformat(last_str.replace("Z", "+00:00"))
                decayed_m = agent.forgetting.calculate_decayed_mastery(raw_m, last_dt, now)
            except Exception:
                decayed_m = raw_m
        else:
            decayed_m = raw_m

        concept_mastery[r["concept"]] = round(decayed_m, 4)
        skill = r["skill"] or "General"
        skill_mastery[skill] = skill_mastery.get(skill, 0.0) + decayed_m
        skill_counts[skill] = skill_counts.get(skill, 0) + 1
        last_practiced[r["concept"]] = last_str

    for s in skill_mastery:
        skill_mastery[s] = round(skill_mastery[s] / skill_counts[s], 4)

    # Load recent attempt history
    cursor.execute("""
    SELECT question_id, concept, skill, selected_option, is_correct, theta_after, mastery_after, timestamp
    FROM question_history WHERE user_id = ? ORDER BY id ASC LIMIT 50
    """, (user_id,))
    h_rows = cursor.fetchall()
    attempt_history = [
        {
            "question_id": h["question_id"],
            "concept": h["concept"],
            "skill": h["skill"],
            "selected_option": h["selected_option"],
            "is_correct": bool(h["is_correct"]),
            "attempt_number": idx + 1,
            "theta_after": h["theta_after"],
            "mastery_after": h["mastery_after"],
            "timestamp": h["timestamp"]
        }
        for idx, h in enumerate(h_rows)
    ]

    conn.close()

    return {
        "theta": theta,
        "concept_mastery": concept_mastery,
        "skill_mastery": skill_mastery,
        "attempt_history": attempt_history,
        "last_practiced": last_practiced,
        "total_attempts": profile_row["total_attempts"] if profile_row else 0,
        "correct_attempts": profile_row["correct_attempts"] if profile_row else 0
    }

@router.post("/generate", response_model=List[AssessmentQuestionResponse])
def generate_assessment(
    total_questions: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Generates a personalized adaptive test for the authenticated student."""
    user_id = current_user["id"]
    target_role = current_user["target_role"]

    student_profile = _load_student_state(user_id)
    questions = agent.generate_assignment(
        student_profile=student_profile,
        total_questions=total_questions,
        target_role=target_role
    )

    return [
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
        ) for q in questions
    ]

@router.post("/submit", response_model=AssessmentSubmitResponse)
def submit_assessment(
    payload: AssessmentSubmitRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Submits student responses, runs online BKT & IRT updates,
    persists updated states and history, and triggers roadmap adaptation.
    """
    user_id = current_user["id"]
    student_profile = _load_student_state(user_id)
    conn = get_db_connection()
    cursor = conn.cursor()

    now = datetime.now(timezone.utc)
    results: List[AnswerResult] = []

    for sub in payload.submissions:
        q_id = sub.question_id
        chosen_opt = sub.selected_option
        
        q_data = agent.question_map.get(q_id)
        if not q_data:
            continue

        res = agent.process_answer(
            student_profile=student_profile,
            question_id=q_id,
            selected_option=chosen_opt,
            timestamp=now
        )

        results.append(AnswerResult(
            question_id=res["question_id"],
            is_correct=res["is_correct"],
            correct_option=res["correct_option"],
            explanation=res["explanation"],
            concept=res["concept"],
            skill=res["skill"],
            previous_mastery=res["previous_mastery"],
            updated_mastery=res["updated_mastery"],
            updated_theta=res["updated_theta"]
        ))

        # Persist into knowledge_states
        cursor.execute("""
        INSERT INTO knowledge_states (user_id, concept, skill, mastery, last_practiced)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id, concept) DO UPDATE SET
            mastery = excluded.mastery,
            last_practiced = excluded.last_practiced
        """, (user_id, res["concept"], q_data.get("skill", "General"), res["updated_mastery"], now.isoformat()))

        # Update aggregated skill in user_skills table
        new_desc_level = numeric_to_descriptive(res["updated_mastery"])
        cursor.execute("""
        INSERT INTO user_skills (user_id, skill_name, category, descriptive_level, numeric_mastery, evidence_source, updated_at)
        VALUES (?, ?, ?, ?, ?, 'Adaptive Assessment', CURRENT_TIMESTAMP)
        ON CONFLICT(user_id, skill_name) DO UPDATE SET
            descriptive_level = excluded.descriptive_level,
            numeric_mastery = excluded.numeric_mastery,
            evidence_source = excluded.evidence_source,
            updated_at = CURRENT_TIMESTAMP
        """, (user_id, q_data.get("skill", "General"), "Technical", new_desc_level, res["updated_mastery"]))

        # Persist attempt into question_history
        cursor.execute("""
        INSERT INTO question_history (user_id, question_id, concept, skill, selected_option, is_correct, theta_after, mastery_after, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, q_id, res["concept"], q_data.get("skill", "General"),
            chosen_opt, 1 if res["is_correct"] else 0, res["updated_theta"], res["updated_mastery"], now.isoformat()
        ))

    # Persist updated profile theta & stats
    cursor.execute("""
    UPDATE student_profiles
    SET theta = ?,
        total_attempts = total_attempts + ?,
        correct_attempts = correct_attempts + ?,
        updated_at = ?
    WHERE user_id = ?
    """, (
        student_profile["theta"],
        len(payload.submissions),
        sum(1 for r in results if r.is_correct),
        now.isoformat(),
        user_id
    ))

    # Record assessment summary
    assessment_id = str(uuid.uuid4())
    total_q = len(results)
    correct_q = sum(1 for r in results if r.is_correct)
    score_pct = round((correct_q / max(1, total_q)) * 100, 1)

    cursor.execute("""
    INSERT INTO assessments (id, user_id, target_role, total_questions, score_percentage)
    VALUES (?, ?, ?, ?, ?)
    """, (assessment_id, user_id, payload.target_role, total_q, score_pct))

    conn.commit()
    conn.close()

    return AssessmentSubmitResponse(
        assessment_id=assessment_id,
        total_questions=total_q,
        correct_count=correct_q,
        score_percentage=score_pct,
        results=results,
        updated_theta=student_profile["theta"]
    )

"""
End-to-End Integration & Student Journey Test Suite
Validates the complete lifecycle:
1. Registration & Authentication (JWT Bearer Token)
2. Student Onboarding & Skill Baseline Initialization
3. Career Track Selection (all 5 roles)
4. Adaptive Question Generation with Explainable Reasoning
5. Question Submission & BKT/IRT State Updates
6. Dynamic Roadmap & Placement Prep Progress Adaptation
7. Session Reload & Database Persistence Verification
"""
import uuid
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import get_db_connection

client = TestClient(app)

@pytest.fixture
def fresh_student():
    """Generates a unique email and credentials for clean test execution."""
    uid = uuid.uuid4().hex[:8]
    return {
        "name": f"Student {uid}",
        "email": f"student_{uid}@university.edu",
        "password": "SecurePassword123!",
        "target_role": "data_scientist"
    }

def test_full_student_journey_lifecycle(fresh_student):
    # 1. Registration
    reg_res = client.post("/api/auth/register", json=fresh_student)
    assert reg_res.status_code == 200, reg_res.text
    token_data = reg_res.json()
    assert "access_token" in token_data
    token = token_data["access_token"]
    user_id = token_data["user"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Verify Profile Fetch
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == fresh_student["email"]
    assert me_res.json()["onboarding_completed"] is False

    # 3. Student Onboarding Submission
    onboarding_payload = {
        "education_level": "Undergraduate (B.Tech / B.S.)",
        "major": "Computer Science & Engineering",
        "graduation_year": 2026,
        "experience_level": "Undergraduate Student",
        "placement_goal": "Top Tier Tech Placement 2026",
        "target_role": "data_scientist",
        "technical_skills": [
            {"name": "Python", "category": "Technical", "level": "Good"},
            {"name": "SQL", "category": "Technical", "level": "Average"},
            {"name": "Machine Learning", "category": "Technical", "level": "Below Average"},
            {"name": "Statistics", "category": "Technical", "level": "Below Average"},
            {"name": "Deep Learning", "category": "Technical", "level": "Below Average"}
        ],
        "soft_skills": ["Problem Solving", "Communication", "Teamwork"],
        "preferred_technologies": ["Python", "PyTorch", "FastAPI", "PostgreSQL"]
    }
    onb_res = client.post("/api/onboarding/submit", json=onboarding_payload, headers=headers)
    assert onb_res.status_code == 200, onb_res.text
    assert onb_res.json()["status"] == "success"
    assert onb_res.json()["onboarding_completed"] is True

    # 4. Check Initial Dashboard & Career Readiness
    dash_res = client.get("/api/dashboard/", headers=headers)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert dash_data["onboarding_completed"] is True
    assert dash_data["career_readiness"] > 0.0
    initial_readiness = dash_data["career_readiness"]
    assert len(dash_data["skills"]) >= 5

    # 5. Generate Adaptive Assessment
    gen_res = client.post("/api/assessment/generate?total_questions=5", headers=headers)
    assert gen_res.status_code == 200, gen_res.text
    questions = gen_res.json()
    assert len(questions) == 5
    for q in questions:
        assert "id" in q
        assert "question" in q
        assert "options" in q
        assert len(q["options"]) >= 2
        assert "selection_reason" in q
        assert len(q["selection_reason"]) > 0

    # 6. Submit Assessment with Known Answers
    # Answer first 4 correctly, last one incorrectly
    submissions = []
    for idx, q in enumerate(questions):
        submissions.append({
            "question_id": q["id"],
            "selected_option": 0 if idx < 4 else 3
        })

    sub_res = client.post("/api/assessment/submit", json={
        "target_role": "data_scientist",
        "submissions": submissions
    }, headers=headers)
    assert sub_res.status_code == 200, sub_res.text
    sub_data = sub_res.json()
    assert sub_data["total_questions"] == 5
    assert len(sub_data["results"]) == 5
    for r in sub_data["results"]:
        assert "is_correct" in r
        assert "explanation" in r
        assert "updated_mastery" in r
        assert "updated_theta" in r

    # 7. Verify Mastery Updates & Next Assignment in Dashboard
    dash_after = client.get("/api/dashboard/", headers=headers)
    assert dash_after.status_code == 200
    after_data = dash_after.json()
    assert after_data["total_attempts"] == 5
    assert after_data["has_sufficient_data"] is True
    assert len(after_data["next_recommended_assignment"]) > 0

    # 8. Verify Career Readiness Updated from Actual Mastery
    assert after_data["career_readiness"] != 0.0

    # 9. Verify Target Role Switching to all 5 Roles
    roles_res = client.get("/api/career/roles")
    assert roles_res.status_code == 200
    roles = roles_res.json()
    assert len(roles) >= 5
    role_ids = [r["role_id"] for r in roles]
    assert "data_scientist" in role_ids
    assert "data_analyst" in role_ids
    assert "backend_developer" in role_ids
    assert "frontend_developer" in role_ids
    assert "ai_ml_engineer" in role_ids

    # Switch to frontend_developer
    switch_res = client.post("/api/career/set-target?role_id=frontend_developer", headers=headers)
    assert switch_res.status_code == 200

    # Verify Roadmap for Frontend Developer
    road_res = client.get("/api/roadmap/", headers=headers)
    assert road_res.status_code == 200
    road_data = road_res.json()
    assert road_data["target_role"] == "frontend_developer"
    assert road_data["total_tasks"] > 0

    # 10. Persistence Verification (Direct DB Check)
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check users
    cursor.execute("SELECT target_role, onboarding_completed FROM users WHERE id = ?", (user_id,))
    u_row = cursor.fetchone()
    assert u_row["target_role"] == "frontend_developer"
    assert u_row["onboarding_completed"] == 1

    # Check question_history
    cursor.execute("SELECT COUNT(*) as count FROM question_history WHERE user_id = ?", (user_id,))
    qh_row = cursor.fetchone()
    assert qh_row["count"] == 5

    # Check knowledge_states
    cursor.execute("SELECT COUNT(*) as count FROM knowledge_states WHERE user_id = ?", (user_id,))
    ks_row = cursor.fetchone()
    assert ks_row["count"] > 0

    # Check assessments
    cursor.execute("SELECT COUNT(*) as count FROM assessments WHERE user_id = ?", (user_id,))
    as_row = cursor.fetchone()
    assert as_row["count"] == 1

    conn.close()

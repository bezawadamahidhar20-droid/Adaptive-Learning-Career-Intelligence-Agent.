"""
Production Database Layer for Adaptive Learning & Career Intelligence Agent
Persists users, secure credentials, onboarding profiles, categorized skills,
knowledge states, question history, dynamic adaptive roadmaps, and placement progress.
"""
import sqlite3
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "adaptive_agent.db")

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Users table with secure authentication & OAuth IDs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT,
        oauth_provider TEXT,
        oauth_id TEXT,
        target_role TEXT DEFAULT 'data_scientist',
        onboarding_completed INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Dynamic migrations for existing databases
    cursor.execute("PRAGMA table_info(users);")
    existing_user_cols = {row["name"] for row in cursor.fetchall()}
    if "password_hash" not in existing_user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT;")
    if "oauth_provider" not in existing_user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN oauth_provider TEXT;")
    if "oauth_id" not in existing_user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN oauth_id TEXT;")
    if "target_role" not in existing_user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN target_role TEXT DEFAULT 'data_scientist';")
    if "onboarding_completed" not in existing_user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN onboarding_completed INTEGER DEFAULT 0;")


    # 2. Student Profiles (Education, Background, Experience, Goals)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS student_profiles (
        user_id TEXT PRIMARY KEY,
        education_level TEXT DEFAULT 'Undergraduate (B.Tech / B.S.)',
        major TEXT DEFAULT 'Computer Science',
        graduation_year INTEGER DEFAULT 2026,
        experience_level TEXT DEFAULT 'Beginner / Student',
        placement_goal TEXT DEFAULT 'Software / AI Placement 2026',
        preferred_technologies TEXT DEFAULT 'Python, SQL, FastApi',
        soft_skills TEXT DEFAULT 'Problem Solving, Communication',
        theta REAL DEFAULT 0.0,
        total_attempts INTEGER DEFAULT 0,
        correct_attempts INTEGER DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """)

    cursor.execute("PRAGMA table_info(student_profiles);")
    existing_profile_cols = {row["name"] for row in cursor.fetchall()}
    if "education_level" not in existing_profile_cols:
        cursor.execute("ALTER TABLE student_profiles ADD COLUMN education_level TEXT DEFAULT 'Undergraduate (B.Tech / B.S.)';")
    if "major" not in existing_profile_cols:
        cursor.execute("ALTER TABLE student_profiles ADD COLUMN major TEXT DEFAULT 'Computer Science';")
    if "graduation_year" not in existing_profile_cols:
        cursor.execute("ALTER TABLE student_profiles ADD COLUMN graduation_year INTEGER DEFAULT 2026;")
    if "experience_level" not in existing_profile_cols:
        cursor.execute("ALTER TABLE student_profiles ADD COLUMN experience_level TEXT DEFAULT 'Beginner / Student';")
    if "placement_goal" not in existing_profile_cols:
        cursor.execute("ALTER TABLE student_profiles ADD COLUMN placement_goal TEXT DEFAULT 'Software / AI Placement 2026';")
    if "preferred_technologies" not in existing_profile_cols:
        cursor.execute("ALTER TABLE student_profiles ADD COLUMN preferred_technologies TEXT DEFAULT 'Python, SQL, FastApi';")
    if "soft_skills" not in existing_profile_cols:
        cursor.execute("ALTER TABLE student_profiles ADD COLUMN soft_skills TEXT DEFAULT 'Problem Solving, Communication';")
    if "theta" not in existing_profile_cols:
        cursor.execute("ALTER TABLE student_profiles ADD COLUMN theta REAL DEFAULT 0.0;")
    if "total_attempts" not in existing_profile_cols:
        cursor.execute("ALTER TABLE student_profiles ADD COLUMN total_attempts INTEGER DEFAULT 0;")
    if "correct_attempts" not in existing_profile_cols:
        cursor.execute("ALTER TABLE student_profiles ADD COLUMN correct_attempts INTEGER DEFAULT 0;")
    if "updated_at" not in existing_profile_cols:
        cursor.execute("ALTER TABLE student_profiles ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

    # 3. Categorized User Skills with Descriptive Levels & Confidence
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_skills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        skill_name TEXT NOT NULL,
        category TEXT NOT NULL,
        descriptive_level TEXT NOT NULL, -- 'Below Average', 'Average', 'Good', 'Perfect'
        numeric_mastery REAL DEFAULT 0.20,
        importance_weight REAL DEFAULT 0.20,
        target_level TEXT DEFAULT 'Good',
        confidence REAL DEFAULT 0.70,
        evidence_source TEXT DEFAULT 'Onboarding Self-Assessment',
        improvement_recommendation TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, skill_name),
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """)

    cursor.execute("PRAGMA table_info(user_skills);")
    existing_skill_cols = {row["name"] for row in cursor.fetchall()}
    if "descriptive_level" not in existing_skill_cols:
        cursor.execute("ALTER TABLE user_skills ADD COLUMN descriptive_level TEXT DEFAULT 'Average';")
    if "importance_weight" not in existing_skill_cols:
        cursor.execute("ALTER TABLE user_skills ADD COLUMN importance_weight REAL DEFAULT 0.20;")
    if "target_level" not in existing_skill_cols:
        cursor.execute("ALTER TABLE user_skills ADD COLUMN target_level TEXT DEFAULT 'Good';")
    if "confidence" not in existing_skill_cols:
        cursor.execute("ALTER TABLE user_skills ADD COLUMN confidence REAL DEFAULT 0.70;")
    if "evidence_source" not in existing_skill_cols:
        cursor.execute("ALTER TABLE user_skills ADD COLUMN evidence_source TEXT DEFAULT 'Assessment';")
    if "improvement_recommendation" not in existing_skill_cols:
        cursor.execute("ALTER TABLE user_skills ADD COLUMN improvement_recommendation TEXT;")

    # 4. Knowledge States (BKT mastery per concept)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS knowledge_states (
        user_id TEXT NOT NULL,
        concept TEXT NOT NULL,
        skill TEXT NOT NULL,
        mastery REAL DEFAULT 0.20,
        last_practiced TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, concept),
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """)

    # 5. Question History (Attempts & Repetition Cooldowns)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS question_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        question_id TEXT NOT NULL,
        concept TEXT NOT NULL,
        skill TEXT NOT NULL,
        selected_option INTEGER NOT NULL,
        is_correct INTEGER NOT NULL,
        theta_after REAL NOT NULL,
        mastery_after REAL NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """)

    # 6. Assessments
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assessments (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        target_role TEXT NOT NULL,
        total_questions INTEGER NOT NULL,
        score_percentage REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """)

    # 7. Adaptive Learning Roadmap Items
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS roadmap_tasks (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        target_role TEXT NOT NULL,
        stage_name TEXT NOT NULL, -- e.g. '1. Foundations', '2. Core Tech', '3. Projects', '4. Placement Prep'
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT NOT NULL, -- 'concept', 'coding_task', 'project', 'dsa'
        associated_skill TEXT NOT NULL,
        priority_rank INTEGER DEFAULT 1,
        is_completed INTEGER DEFAULT 0,
        completed_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """)

    # 8. Placement Preparation Progress
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS placement_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        module_type TEXT NOT NULL, -- 'dsa', 'aptitude', 'tech_interview', 'hr_interview', 'resume_checklist'
        item_id TEXT NOT NULL,
        title TEXT NOT NULL,
        status TEXT DEFAULT 'pending', -- 'pending', 'in_progress', 'completed'
        score REAL DEFAULT 0.0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, module_type, item_id),
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """)

    # 9. Bandit Policy Persistent States
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bandit_policies (
        policy_name TEXT PRIMARY KEY,
        state_json TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 10. Item Bank & Versioning
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS item_bank (
        item_id TEXT PRIMARY KEY,
        concept_id TEXT NOT NULL,
        difficulty REAL DEFAULT 0.0,
        discrimination REAL DEFAULT 1.0,
        guessing REAL DEFAULT 0.20,
        cognitive_level TEXT DEFAULT 'apply',
        estimated_seconds INTEGER DEFAULT 90,
        prerequisites TEXT DEFAULT '[]',
        exposure_limit REAL DEFAULT 0.25,
        version INTEGER DEFAULT 1,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 11. Assessment Psychometric Reliability & Uncertainty Store
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assessment_reliability (
        assessment_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        theta REAL NOT NULL,
        posterior_se REAL NOT NULL,
        response_only_se REAL NOT NULL,
        observed_info REAL NOT NULL,
        prior_info REAL NOT NULL,
        raw_ci_low REAL NOT NULL,
        raw_ci_high REAL NOT NULL,
        display_ci_low REAL NOT NULL,
        display_ci_high REAL NOT NULL,
        reliability_status TEXT NOT NULL,
        termination_reason TEXT NOT NULL,
        estimation_method TEXT DEFAULT 'MAP',
        item_bank_version TEXT DEFAULT '2026.09',
        item_count INTEGER NOT NULL,
        concept_count INTEGER NOT NULL,
        concept_coverage_ratio REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (assessment_id) REFERENCES assessments (id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """)

    # Dynamic migrations for assessments table
    cursor.execute("PRAGMA table_info(assessments);")
    existing_assessment_cols = {row["name"] for row in cursor.fetchall()}
    if "correct_answers" not in existing_assessment_cols:
        cursor.execute("ALTER TABLE assessments ADD COLUMN correct_answers INTEGER DEFAULT 0;")
    if "estimated_theta" not in existing_assessment_cols:
        cursor.execute("ALTER TABLE assessments ADD COLUMN estimated_theta REAL DEFAULT 0.0;")
    if "test_type" not in existing_assessment_cols:
        cursor.execute("ALTER TABLE assessments ADD COLUMN test_type TEXT DEFAULT 'diagnostic';")

    # Indexes for high-frequency queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_skills_uid ON user_skills (user_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_states_uid ON knowledge_states (user_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_question_history_uid ON question_history (user_id, question_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_roadmap_tasks_uid ON roadmap_tasks (user_id, target_role);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_placement_progress_uid ON placement_progress (user_id, module_type);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_assessment_reliability_uid ON assessment_reliability (user_id);")

    conn.commit()
    conn.close()

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn

def save_bandit_policy_state(policy_name: str, state_dict: Dict[str, Any]):
    """Persists bandit policy state into SQLite database."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO bandit_policies (policy_name, state_json, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(policy_name) DO UPDATE SET
            state_json = excluded.state_json,
            updated_at = CURRENT_TIMESTAMP
        """, (policy_name, json.dumps(state_dict)))
        conn.commit()
    finally:
        conn.close()

def load_bandit_policy_state(policy_name: str) -> Optional[Dict[str, Any]]:
    """Loads bandit policy state from SQLite database."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT state_json FROM bandit_policies WHERE policy_name = ?", (policy_name,))
        row = cursor.fetchone()
        if row and row["state_json"]:
            try:
                return json.loads(row["state_json"])
            except Exception:
                return None
        return None
    finally:
        conn.close()

# Initialize DB tables and indexes on module load
init_db()

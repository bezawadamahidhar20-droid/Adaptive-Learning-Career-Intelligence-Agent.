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

    conn.commit()
    conn.close()

# Initialize DB on module load
init_db()

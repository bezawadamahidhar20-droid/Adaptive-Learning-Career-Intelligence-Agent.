"""
SQLite Database Layer for Adaptive Learning Agent
Persists student profiles, knowledge states, question attempt logs, and assessments.
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
    
    # 1. Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        target_role TEXT DEFAULT 'data_scientist',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Student Profiles
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS student_profiles (
        user_id TEXT PRIMARY KEY,
        theta REAL DEFAULT 0.0,
        total_attempts INTEGER DEFAULT 0,
        correct_attempts INTEGER DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    );
    """)

    # 3. Knowledge States (BKT mastery per concept)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS knowledge_states (
        user_id TEXT,
        concept TEXT,
        skill TEXT,
        mastery REAL DEFAULT 0.20,
        last_practiced TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, concept),
        FOREIGN KEY (user_id) REFERENCES users (id)
    );
    """)

    # 4. Question History (attempts & cooldowns)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS question_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        question_id TEXT,
        concept TEXT,
        skill TEXT,
        selected_option INTEGER,
        is_correct INTEGER,
        theta_after REAL,
        mastery_after REAL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    );
    """)

    # 5. Assessments
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assessments (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        target_role TEXT,
        total_questions INTEGER,
        score_percentage REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    );
    """)

    conn.commit()
    conn.close()

# Initialize DB on module load
init_db()

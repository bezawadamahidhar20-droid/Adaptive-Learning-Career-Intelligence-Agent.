"""
Auth and Student Profile Router
"""
import uuid
import sqlite3
from fastapi import APIRouter, HTTPException, Depends
from ..database import get_db_connection
from ..schemas import UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserResponse)
def register_user(payload: UserCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if user with email exists
    cursor.execute("SELECT id, name, email, target_role FROM users WHERE email = ?", (payload.email,))
    existing = cursor.fetchone()
    if existing:
        conn.close()
        return UserResponse(
            id=existing["id"],
            name=existing["name"],
            email=existing["email"],
            target_role=existing["target_role"]
        )

    user_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO users (id, name, email, target_role) VALUES (?, ?, ?, ?)",
        (user_id, payload.name, payload.email, payload.target_role)
    )
    cursor.execute(
        "INSERT INTO student_profiles (user_id, theta, total_attempts, correct_attempts) VALUES (?, 0.0, 0, 0)",
        (user_id,)
    )
    conn.commit()
    conn.close()

    return UserResponse(
        id=user_id,
        name=payload.name,
        email=payload.email,
        target_role=payload.target_role
    )

@router.get("/user/{user_id}", response_model=UserResponse)
def get_user(user_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, target_role FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        id=row["id"],
        name=row["name"],
        email=row["email"],
        target_role=row["target_role"]
    )

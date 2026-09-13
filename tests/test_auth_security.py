import pytest
import time
from backend.security import (
    hash_password, verify_password, create_access_token, decode_access_token
)
from backend.database import get_db_connection, init_db

def setup_module():
    init_db()

def test_password_hashing_and_verification():
    raw_pw = "SuperSecurePass123!"
    pw_hash = hash_password(raw_pw)
    
    assert pw_hash != raw_pw
    assert verify_password(raw_pw, pw_hash) is True
    assert verify_password("WrongPassword123", pw_hash) is False

def test_jwt_token_generation_and_validation():
    payload = {"sub": "user_12345", "email": "student@university.edu"}
    token = create_access_token(payload)
    
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user_12345"
    assert decoded["email"] == "student@university.edu"

def test_jwt_tampered_token_rejection():
    token = create_access_token({"sub": "user_12345"})
    parts = token.split('.')
    # Tamper with payload
    tampered = f"{parts[0]}.eyJzdWIiOiAiaGFja2VyIn0.{parts[2]}"
    assert decode_access_token(tampered) is None

def test_jwt_invalid_format_rejection():
    assert decode_access_token("invalid.token") is None
    assert decode_access_token("") is None

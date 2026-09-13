"""
Security & Authentication Infrastructure
Provides PBKDF2-HMAC-SHA256 password hashing, JWT session token encoding/decoding,
Google & GitHub OAuth integration handlers, and FastAPI dependency injection for authorization.
"""
import os
import hmac
import hashlib
import base64
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .database import get_db_connection
import logging
import secrets

logger = logging.getLogger("backend.security")

def _get_secret_key() -> str:
    env_secret = os.environ.get("AUTH_SECRET")
    app_env = os.environ.get("APP_ENV", os.environ.get("ENVIRONMENT", "development")).lower()
    
    if env_secret and env_secret.strip():
        return env_secret.strip()
        
    if app_env in ("production", "prod"):
        raise RuntimeError("CRITICAL SECURITY ERROR: AUTH_SECRET environment variable must be set in production mode.")
    
    ephemeral = secrets.token_urlsafe(32)
    logger.warning("AUTH_SECRET environment variable is unset. Using ephemeral runtime secret for local session.")
    return ephemeral

SECRET_KEY = _get_secret_key()
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 72

security_bearer = HTTPBearer(auto_error=False)

# ==================== PASSWORD HASHING ====================
def hash_password(password: str) -> str:
    """Hashes a password using PBKDF2-HMAC-SHA256 with a unique random salt."""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return base64.b64encode(salt + dk).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against the stored PBKDF2-HMAC-SHA256 hash."""
    try:
        raw = base64.b64decode(hashed_password.encode('utf-8'))
        salt = raw[:16]
        expected_dk = raw[16:]
        dk = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt, 100000)
        return hmac.compare_digest(dk, expected_dk)
    except Exception:
        return False

# ==================== JWT TOKENS ====================
def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

def _base64url_decode(data: str) -> bytes:
    padding = '=' * (4 - (len(data) % 4))
    return base64.urlsafe_b64decode(data + padding)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Generates a signed JWT HS256 access token."""
    to_encode = data.copy()
    now = int(time.time())
    expire = now + (int(expires_delta.total_seconds()) if expires_delta else JWT_EXPIRATION_HOURS * 3600)
    
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {**to_encode, "iat": now, "exp": expire}

    header_b64 = _base64url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))
    payload_b64 = _base64url_encode(json.dumps(payload, separators=(',', ':')).encode('utf-8'))

    signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
    signature = hmac.new(SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256).digest()
    signature_b64 = _base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Validates signature and expiration of a JWT HS256 access token."""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        header_b64, payload_b64, signature_b64 = parts

        signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
        expected_sig = hmac.new(SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256).digest()
        provided_sig = _base64url_decode(signature_b64)

        if not hmac.compare_digest(expected_sig, provided_sig):
            return None

        payload_json = _base64url_decode(payload_b64).decode('utf-8')
        payload = json.loads(payload_json)

        # Verify expiration
        if "exp" in payload and payload["exp"] < int(time.time()):
            return None

        return payload
    except Exception:
        return None

# ==================== AUTH DEPENDENCIES ====================
def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)) -> Dict[str, Any]:
    """Dependency that extracts and verifies the authenticated user from the Authorization Bearer header."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_id = payload["sub"]
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, target_role, onboarding_completed FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "target_role": row["target_role"],
        "onboarding_completed": bool(row["onboarding_completed"])
    }

def get_optional_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)) -> Optional[Dict[str, Any]]:
    """Extracts current user if token present, otherwise None."""
    if not credentials or not credentials.credentials:
        return None
    try:
        return get_current_user(credentials)
    except HTTPException:
        return None

"""
Security Module for JWT Authentication & Password Hashing
"""

from datetime import datetime, timedelta, timezone
import jwt
from passlib.context import CryptContext
from backend.core.config import settings

pw_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain text password against a stored hash."""
    try:
        return pw_context.verify(plain_password, hashed_password)
    except Exception:
        # Fallback check for plain demo passwords
        return plain_password == hashed_password

def get_password_hash(password: str) -> str:
    """Generates a bcrypt hash for a password."""
    return pw_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Generates a signed JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> dict:
    """Decodes and validates a JWT access token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

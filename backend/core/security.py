"""Security, password hashing, JWT operations, and RBAC authorization dependencies."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from backend.core.config import settings
from backend.core.exceptions import AuthenticationError, PermissionDeniedError

# OAuth2 scheme for Bearer token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


class TokenData(BaseModel):
    user_id: str
    email: str
    role: str
    exp: Optional[int] = None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Generate bcrypt hash from plain text password."""
    # Truncate password to 72 bytes if needed (bcrypt spec limit)
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Generate JWT access token signed with HMAC SHA-256."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": now})
    secret_key = settings.get_jwt_secret_key()
    encoded_jwt = jwt.encode(
        to_encode,
        secret_key,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> TokenData:
    """Decode and validate a JWT access token."""
    try:
        secret_key = settings.get_jwt_secret_key()
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        role: str = payload.get("role")
        
        if user_id is None or email is None or role is None:
            raise AuthenticationError("Invalid token payload structure")
            
        return TokenData(user_id=user_id, email=email, role=role, exp=payload.get("exp"))
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Authentication token has expired")
    except jwt.InvalidTokenError:
        raise AuthenticationError("Could not validate authentication token")


def get_current_user_token(token: str = Depends(oauth2_scheme)) -> TokenData:
    """FastAPI dependency: Extracts and verifies JWT from Bearer header."""
    return decode_access_token(token)


def require_role(allowed_roles: List[str]):
    """FastAPI RBAC dependency factory to enforce user role authorizations."""
    def role_checker(token_data: TokenData = Depends(get_current_user_token)) -> TokenData:
        if token_data.role not in allowed_roles:
            raise PermissionDeniedError(
                f"Role '{token_data.role}' is not authorized to access this resource. Required: {allowed_roles}"
            )
        return token_data
    return role_checker

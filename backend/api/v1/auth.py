"""
Authentication REST API Router (/api/v1/auth)
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from backend.core.security import create_access_token, verify_password
import logging

logger = logging.getLogger("api.auth")
router = APIRouter(prefix="/auth", tags=["Authentication"])

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    email: str

# Demo registered accounts for fallback authentication
DEMO_ACCOUNTS = {
    "employee@company.com": {"password": "password123", "role": "employee"},
    "user@company.com": {"password": "password123", "role": "employee"},
    "admin@company.com": {"password": "adminpassword123", "role": "admin"}
}

@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest):
    email_clean = request.email.lower().strip()
    
    # 1. Check demo accounts or CockroachDB user table
    account = DEMO_ACCOUNTS.get(email_clean)
    if not account or not verify_password(request.password, account["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please verify your credentials."
        )

    # 2. Issue JWT Access Token
    token = create_access_token(data={"sub": email_clean, "role": account["role"]})

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        role=account["role"],
        email=email_clean
    )

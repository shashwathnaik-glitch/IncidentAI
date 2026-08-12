"""Authentication REST endpoints."""

from uuid import UUID
from fastapi import APIRouter, Depends, status
from backend.core.dependencies import get_auth_service
from backend.core.security import TokenData, get_current_user_token
from backend.schemas.auth import LoginRequest, TokenResponse, UserResponse
from backend.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def login(
    login_req: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> TokenResponse:
    """
    Authenticate an Employee or Admin user.
    Returns a signed JWT access token and user role.
    """
    return auth_service.authenticate_user(login_req)


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
def get_current_user_profile(
    current_token: TokenData = Depends(get_current_user_token),
    auth_service: AuthService = Depends(get_auth_service)
) -> UserResponse:
    """
    Retrieve authenticated user profile.
    Requires a valid JWT Bearer token.
    """
    return auth_service.get_user_profile(UUID(current_token.user_id))

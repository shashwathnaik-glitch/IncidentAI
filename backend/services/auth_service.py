"""Service layer for authentication and user token management."""

from uuid import UUID
from backend.core.exceptions import AuthenticationError, NotFoundError
from backend.core.security import create_access_token, verify_password
from backend.interfaces.db_interface import IDatabaseRepository
from backend.schemas.auth import LoginRequest, TokenResponse, UserResponse


class AuthService:
    def __init__(self, db_repo: IDatabaseRepository):
        self.db_repo = db_repo

    def authenticate_user(self, login_req: LoginRequest) -> TokenResponse:
        """Authenticate user credentials and issue a signed JWT token."""
        user = self.db_repo.get_user_by_email(login_req.email)
        if not user:
            raise AuthenticationError("Invalid email or password")
            
        if not verify_password(login_req.password, user.password_hash):
            raise AuthenticationError("Invalid email or password")

        # Generate JWT with user_id, email, and role
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
        }
        access_token = create_access_token(data=token_data)

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=user.id,
            email=user.email,
            role=user.role,
            expires_in_seconds=28800  # 8 hours
        )

    def get_user_profile(self, user_id: UUID) -> UserResponse:
        """Retrieve user profile by ID."""
        user = self.db_repo.get_user_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")

        return UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role,
            department=user.department,
            created_at=user.created_at
        )

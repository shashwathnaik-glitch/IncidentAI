"""Unit and integration tests for Role-Based Access Control (RBAC) authorization logic."""

import pytest
from fastapi import status
from backend.core.exceptions import AuthenticationError, PermissionDeniedError
from backend.core.security import create_access_token, decode_access_token, require_role


def test_token_creation_and_decoding():
    """Test encoding and decoding JWT token payload."""
    payload = {"sub": "123", "email": "admin@company.com", "role": "admin"}
    token = create_access_token(data=payload)
    token_data = decode_access_token(token)
    assert token_data.user_id == "123"
    assert token_data.email == "admin@company.com"
    assert token_data.role == "admin"


def test_invalid_token_decoding():
    """Test decode_access_token raises AuthenticationError on bogus token."""
    with pytest.raises(AuthenticationError):
        decode_access_token("not.a.valid.jwt")


def test_require_role_allowed():
    """Test require_role passes when token role is in allowed list."""
    role_checker = require_role(allowed_roles=["admin"])
    payload = {"sub": "123", "email": "admin@company.com", "role": "admin"}
    token = create_access_token(data=payload)
    token_data = decode_access_token(token)

    result = role_checker(token_data=token_data)
    assert result.role == "admin"


def test_require_role_denied():
    """Test require_role raises PermissionDeniedError when role is not allowed."""
    role_checker = require_role(allowed_roles=["admin"])
    payload = {"sub": "123", "email": "emp@company.com", "role": "employee"}
    token = create_access_token(data=payload)
    token_data = decode_access_token(token)

    with pytest.raises(PermissionDeniedError):
        role_checker(token_data=token_data)


def test_employee_attempting_admin_endpoint(client):
    """Test employee user is rejected with HTTP 403 Forbidden when accessing admin endpoint."""
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "employee@company.com", "password": "Password123!"}
    )
    emp_token = login_res.json()["access_token"]

    response = client.get(
        "/api/v1/admin/dashboard",
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    data = response.json()
    assert data["success"] is False
    assert "PermissionDeniedError" in data["error"]["type"]


def test_admin_accessing_allowed_endpoint(client):
    """Test admin user is granted access with HTTP 200 OK when accessing admin endpoint."""
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@company.com", "password": "AdminPassword123!"}
    )
    admin_token = login_res.json()["access_token"]

    response = client.get(
        "/api/v1/admin/dashboard",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "active"
    assert "metrics" in data

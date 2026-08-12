"""Unit and integration tests for authentication service and API endpoints."""

from fastapi import status


def test_valid_employee_login(client):
    """Test successful login with valid employee credentials."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "employee@company.com", "password": "Password123!"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["role"] == "employee"
    assert data["email"] == "employee@company.com"


def test_valid_admin_login(client):
    """Test successful login with valid admin credentials."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@company.com", "password": "AdminPassword123!"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["role"] == "admin"
    assert data["email"] == "admin@company.com"


def test_login_invalid_credentials(client):
    """Test login failure with wrong password or non-existent user."""
    # Wrong password
    wrong_pwd_res = client.post(
        "/api/v1/auth/login",
        json={"email": "employee@company.com", "password": "WrongPassword!"}
    )
    assert wrong_pwd_res.status_code == status.HTTP_401_UNAUTHORIZED
    assert wrong_pwd_res.json()["success"] is False

    # Non-existent user
    non_existent_res = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@company.com", "password": "Password123!"}
    )
    assert non_existent_res.status_code == status.HTTP_401_UNAUTHORIZED
    assert non_existent_res.json()["success"] is False


def test_unauthorized_endpoint_access(client):
    """Test protected endpoints reject unauthenticated access (missing or invalid Bearer token)."""
    # Missing header
    res_missing = client.get("/api/v1/auth/me")
    assert res_missing.status_code == status.HTTP_401_UNAUTHORIZED

    # Invalid token string
    res_invalid = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer bogus_jwt_token_payload"}
    )
    assert res_invalid.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_current_user_me_success(client):
    """Test retrieving profile for authenticated user."""
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "employee@company.com", "password": "Password123!"}
    )
    token = login_res.json()["access_token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == "employee@company.com"
    assert data["name"] == "Jane Doe"
    assert data["role"] == "employee"

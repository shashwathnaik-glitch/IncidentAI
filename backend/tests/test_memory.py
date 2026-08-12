"""Dedicated unit and integration tests for memory search endpoint and MemoryService."""

from fastapi import status


def get_auth_token(client, email="employee@company.com", password="Password123!"):
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password}
    )
    return login_res.json()["access_token"]


def test_memory_search_unauthenticated(client):
    """Verify GET /api/v1/memory/search requires valid authentication token."""
    res = client.get("/api/v1/memory/search?q=database")
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


def test_memory_search_success(client):
    """Verify authenticated memory search proxies call via MemoryService to IAIServiceInterface."""
    token = get_auth_token(client)
    res = client.get(
        "/api/v1/memory/search?q=latency+spike&limit=5",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["query"] == "latency spike"
    assert "matches" in data
    assert len(data["matches"]) > 0
    assert data["matches"][0]["similarity_score"] == 0.92


def test_memory_search_input_validation(client):
    """Verify query string length validation on /memory/search."""
    token = get_auth_token(client)
    res = client.get(
        "/api/v1/memory/search?q=a",  # min_length=2 required
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

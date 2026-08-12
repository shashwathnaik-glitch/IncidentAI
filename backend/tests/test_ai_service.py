"""Unit and integration tests for AIService and GET /api/v1/memory/search endpoint."""

from fastapi import status
from backend.schemas.memory import MemorySearchQuery
from backend.services.ai_service import AIService
from backend.tests.mocks.mock_ai_interface import MockAIInterface


def test_ai_service_proxy():
    """Test AIService delegates search_memory to IAIServiceInterface."""
    mock_ai = MockAIInterface()
    ai_service = AIService(ai_interface=mock_ai)
    query = MemorySearchQuery(query="database latency spike", limit=3)
    response = ai_service.search_memory(query)

    assert response.query == "database latency spike"
    assert response.total_results == 1
    assert len(response.matches) == 1
    assert response.matches[0].similarity_score == 0.92


def test_memory_search_endpoint_unauthenticated(client):
    """Test GET /api/v1/memory/search requires valid authentication token."""
    response = client.get("/api/v1/memory/search?q=database")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_memory_search_endpoint_authenticated(client):
    """Test GET /api/v1/memory/search proxying when properly authenticated."""
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "employee@company.com", "password": "Password123!"}
    )
    token = login_res.json()["access_token"]

    response = client.get(
        "/api/v1/memory/search?q=network+timeout",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["query"] == "network timeout"
    assert "matches" in data
    assert len(data["matches"]) > 0
    assert data["matches"][0]["similarity_score"] == 0.92

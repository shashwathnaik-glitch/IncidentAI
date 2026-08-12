"""Unit tests for Backend Health Check endpoint."""

from fastapi import status


def test_health_check_endpoint(client):
    """Test GET /health returns HTTP 200 and valid health check payload."""
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "version" in data
    assert "environment" in data

"""Dedicated unit and integration tests for AI analysis and action approval endpoints."""

from uuid import uuid4
from fastapi import status


def get_auth_token(client, email="employee@company.com", password="Password123!"):
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password}
    )
    return login_res.json()["access_token"]


def test_ai_analyze_endpoint_unauthenticated(client):
    """Verify POST /api/v1/ai/analyze requires authentication."""
    res = client.post(
        "/api/v1/ai/analyze",
        json={"incident_id": str(uuid4())}
    )
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


def test_ai_analyze_endpoint_success(client):
    """Verify POST /api/v1/ai/analyze delegates to AIService and returns response model."""
    token = get_auth_token(client)
    incident_id = str(uuid4())

    res = client.post(
        "/api/v1/ai/analyze",
        json={
            "incident_id": incident_id,
            "error_logs": "ConnectionTimeout on port 5432",
            "environment": "production"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["incident_id"] == incident_id
    assert "recommended_solution" in data
    assert "explanation" in data
    assert "confidence_score" in data
    assert "historical_evidence" in data
    assert "action_id" in data


def test_ai_approve_endpoint_unauthenticated(client):
    """Verify POST /api/v1/ai/approve requires authentication."""
    res = client.post(
        "/api/v1/ai/approve",
        json={"action_id": "ACT-12345"}
    )
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


def test_ai_approve_endpoint_success(client):
    """Verify POST /api/v1/ai/approve delegates to AIService and returns approval confirmation."""
    token = get_auth_token(client)
    res = client.post(
        "/api/v1/ai/approve",
        json={
            "action_id": "ACT-98234-RESTART",
            "reasoning": "Approved after reviewing memory evidence."
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["action_id"] == "ACT-98234-RESTART"
    assert data["status"] == "approved"
    assert "approved_by" in data
    assert "approved_at" in data

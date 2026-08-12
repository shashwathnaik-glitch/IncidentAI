"""Dedicated unit and integration tests for Repeated Incident Detection support."""

from uuid import uuid4
from fastapi import status


def get_token(client, email="employee@company.com", password="Password123!"):
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password}
    )
    return login_res.json()["access_token"]


def test_detect_repeated_incidents_unauthenticated(client):
    """Verify GET /api/v1/incidents/{id}/repeated requires authentication."""
    bogus_id = str(uuid4())
    res = client.get(f"/api/v1/incidents/{bogus_id}/repeated")
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


def test_detect_repeated_incidents_not_found(client):
    """Verify GET /api/v1/incidents/{id}/repeated returns 404 for non-existent incident."""
    token = get_token(client)
    bogus_id = str(uuid4())
    res = client.get(
        f"/api/v1/incidents/{bogus_id}/repeated",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == status.HTTP_404_NOT_FOUND


def test_detect_repeated_incidents_detection_flow(client):
    """
    Test repeated incident detection when multiple incidents in the same category exist.
    Verifies repeat_count, similar_incident_references, recent_occurrences,
    common_solution_attempts, and historical_outcomes.
    """
    token = get_token(client)

    # 1. Create Incident 1 in "Database" category
    inc1_res = client.post(
        "/api/v1/incidents",
        json={
            "title": "PostgreSQL Connection Limit Exceeded",
            "description": "Max connections threshold reached on primary DB pool",
            "category": "Database",
            "severity": "P2"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert inc1_res.status_code == status.HTTP_201_CREATED
    inc1_id = inc1_res.json()["id"]

    # Record solution attempt on Incident 1
    att1_res = client.post(
        f"/api/v1/incidents/{inc1_id}/attempts",
        json={
            "solution_text": "Increased max_connections setting to 500",
            "outcome": "success"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert att1_res.status_code == status.HTTP_201_CREATED

    # 2. Create Incident 2 in "Database" category (Repeated occurrence)
    inc2_res = client.post(
        "/api/v1/incidents",
        json={
            "title": "PostgreSQL Idle Connection Timeout",
            "description": "Unclosed connections causing memory pressure on DB server",
            "category": "Database",
            "severity": "P2"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert inc2_res.status_code == status.HTTP_201_CREATED
    inc2_id = inc2_res.json()["id"]

    # 3. Call repeated incident detection endpoint on Incident 2
    rep_res = client.get(
        f"/api/v1/incidents/{inc2_id}/repeated",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert rep_res.status_code == status.HTTP_200_OK
    data = rep_res.json()

    assert data["incident_id"] == inc2_id
    assert data["category"] == "Database"
    assert data["repeat_count"] >= 2
    assert data["is_repeated_incident"] is True
    assert len(data["similar_incident_references"]) >= 2
    assert len(data["recent_occurrences"]) >= 2
    assert "Increased max_connections setting to 500" in data["common_solution_attempts"]
    assert "success" in data["historical_outcomes"]

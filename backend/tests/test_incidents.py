"""Unit and integration tests for Incident API endpoints and service logic."""

from uuid import uuid4
from fastapi import status


def get_auth_token(client, email="employee@company.com", password="Password123!"):
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password}
    )
    return login_res.json()["access_token"]


def test_create_incident_success(client):
    token = get_auth_token(client)
    payload = {
        "title": "High latency on auth service",
        "description": "API Gateway reporting p99 latency > 2500ms on authentication endpoint",
        "category": "Authentication",
        "severity": "P2"
    }
    response = client.post(
        "/api/v1/incidents",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["title"] == payload["title"]
    assert data["category"] == "Authentication"
    assert data["severity"] == "P2"
    assert data["status"] == "open"
    assert "id" in data
    assert "reported_by" in data


def test_create_incident_unauthenticated(client):
    payload = {
        "title": "Unauthenticated incident test",
        "description": "This should fail because no JWT header is present",
        "category": "Security",
        "severity": "P1"
    }
    response = client.post("/api/v1/incidents", json=payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_incident_success(client):
    token = get_auth_token(client)
    create_res = client.post(
        "/api/v1/incidents",
        json={
            "title": "Disk space warning",
            "description": "Root partition usage exceeded 90% threshold on node-04",
            "category": "Storage",
            "severity": "P3"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    incident_id = create_res.json()["id"]

    get_res = client.get(
        f"/api/v1/incidents/{incident_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert get_res.status_code == status.HTTP_200_OK
    assert get_res.json()["id"] == incident_id
    assert get_res.json()["title"] == "Disk space warning"


def test_get_incident_not_found(client):
    token = get_auth_token(client)
    bogus_id = str(uuid4())
    get_res = client.get(
        f"/api/v1/incidents/{bogus_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert get_res.status_code == status.HTTP_404_NOT_FOUND


def test_list_incidents_filtering(client):
    token = get_auth_token(client)

    # Create distinct incidents
    client.post(
        "/api/v1/incidents",
        json={"title": "DB Outage P1", "description": "Database cluster split brain event", "category": "Database", "severity": "P1"},
        headers={"Authorization": f"Bearer {token}"}
    )
    client.post(
        "/api/v1/incidents",
        json={"title": "UI glitch P4", "description": "Minor font rendering issue on mobile view", "category": "Frontend", "severity": "P4"},
        headers={"Authorization": f"Bearer {token}"}
    )

    list_res = client.get(
        "/api/v1/incidents?severity=P1",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert list_res.status_code == status.HTTP_200_OK
    incidents = list_res.json()
    assert all(inc["severity"] == "P1" for inc in incidents)


def test_update_incident_details_success(client):
    """Test updating incident title, description, category, severity via PUT /api/v1/incidents/{id}."""
    token = get_auth_token(client)
    create_res = client.post(
        "/api/v1/incidents",
        json={
            "title": "Initial Title",
            "description": "Initial description of incident symptom",
            "category": "Networking",
            "severity": "P3"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    incident_id = create_res.json()["id"]

    put_res = client.put(
        f"/api/v1/incidents/{incident_id}",
        json={
            "title": "Updated Critical Title",
            "severity": "P1"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert put_res.status_code == status.HTTP_200_OK
    data = put_res.json()
    assert data["title"] == "Updated Critical Title"
    assert data["severity"] == "P1"


def test_update_incident_status_success(client):
    token = get_auth_token(client)
    create_res = client.post(
        "/api/v1/incidents",
        json={
            "title": "Memory leak in queue consumer",
            "description": "Worker processes being OOM killed every 4 hours",
            "category": "Infrastructure",
            "severity": "P2"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    incident_id = create_res.json()["id"]

    patch_res = client.patch(
        f"/api/v1/incidents/{incident_id}/status",
        json={"status": "investigating"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert patch_res.status_code == status.HTTP_200_OK
    assert patch_res.json()["status"] == "investigating"


def test_update_incident_status_not_found(client):
    token = get_auth_token(client)
    bogus_id = str(uuid4())
    patch_res = client.patch(
        f"/api/v1/incidents/{bogus_id}/status",
        json={"status": "closed"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert patch_res.status_code == status.HTTP_404_NOT_FOUND


def test_incident_validation_errors(client):
    """Test validation errors on missing fields or invalid UUID format."""
    token = get_auth_token(client)

    # Missing title & description
    invalid_payload = client.post(
        "/api/v1/incidents",
        json={"category": "Database"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert invalid_payload.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Invalid UUID format
    invalid_uuid = client.get(
        "/api/v1/incidents/not-a-valid-uuid",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert invalid_uuid.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

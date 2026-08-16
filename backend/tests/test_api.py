"""
Unit tests for IncidentMind FastAPI API endpoints (/api/v1/auth, /api/v1/incidents, /api/v1/ai, /api/v1/admin)
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "IncidentMind API Gateway"
    assert data["status"] == "online"

def test_auth_login_valid_credentials():
    payload = {
        "email": "employee@company.com",
        "password": "password123"
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "employee"
    assert data["token_type"] == "bearer"

def test_auth_login_invalid_credentials():
    payload = {
        "email": "employee@company.com",
        "password": "wrongpassword"
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]

def test_admin_dashboard_endpoint():
    response = client.get("/api/v1/admin/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert "activeIncidents" in data
    assert "solutionEffectiveness" in data
    assert data["nodeClusterHealth"] == "HEALTHY"

def test_admin_users_endpoint():
    response = client.get("/api/v1/admin/users")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["role"] in ["admin", "employee"]

def test_ai_analyze_endpoint():
    payload = {
        "title": "CockroachDB connection issue",
        "description": "Connection pool size reached max limits during load spike",
        "logs": "FATAL: sorry, too many clients already"
    }
    response = client.post("/api/v1/ai/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "root_cause" in data
    assert "confidence" in data
    assert "suggested_fix" in data

def test_incidents_create_validation():
    payload = {
        "title": "",
        "description": "   "
    }
    response = client.post("/api/v1/incidents", json=payload)
    assert response.status_code == 400
    assert "required" in response.json()["detail"].lower()

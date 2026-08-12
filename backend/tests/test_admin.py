"""Dedicated unit and integration tests for Admin API endpoints and metrics calculations."""

from fastapi import status


def get_token(client, email, password):
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password}
    )
    return login_res.json()["access_token"]


def test_admin_dashboard_unauthenticated(client):
    """Verify GET /api/v1/admin/dashboard requires authentication."""
    res = client.get("/api/v1/admin/dashboard")
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


def test_admin_dashboard_employee_forbidden(client):
    """Verify employee role user is rejected with HTTP 403 Forbidden on dashboard and analytics endpoints."""
    token = get_token(client, "employee@company.com", "Password123!")
    
    dash_res = client.get(
        "/api/v1/admin/dashboard",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert dash_res.status_code == status.HTTP_403_FORBIDDEN

    analytics_res = client.get(
        "/api/v1/admin/analytics",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert analytics_res.status_code == status.HTTP_403_FORBIDDEN


def test_admin_dashboard_admin_success(client):
    """Verify admin role user receives HTTP 200 OK and valid SystemMetrics response."""
    token = get_token(client, "admin@company.com", "AdminPassword123!")
    res = client.get(
        "/api/v1/admin/dashboard",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["status"] == "active"
    assert "metrics" in data
    assert "solution_analytics" in data
    assert "employee_usage" in data
    assert "ai_usage" in data
    assert "system_status" in data

    metrics = data["metrics"]
    assert "total_incidents" in metrics
    assert "active_incidents" in metrics
    assert "open_incidents" in metrics
    assert "resolved_incidents" in metrics
    assert "resolution_rate_pct" in metrics
    assert "avg_mttr_minutes" in metrics


def test_admin_analytics_endpoint_success(client):
    """Verify GET /api/v1/admin/analytics returns comprehensive analytics for admin user."""
    token = get_token(client, "admin@company.com", "AdminPassword123!")
    res = client.get(
        "/api/v1/admin/analytics",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert "solution_analytics" in data
    assert "employee_usage" in data
    assert "ai_usage" in data
    assert "system_status" in data


def test_admin_dashboard_metrics_calculation(client):
    """Verify metrics calculation when incidents and solution attempts exist in database repository."""
    emp_token = get_token(client, "employee@company.com", "Password123!")
    admin_token = get_token(client, "admin@company.com", "AdminPassword123!")

    # Create an incident
    create_res = client.post(
        "/api/v1/incidents",
        json={
            "title": "API Gateway Timeout",
            "description": "Gateway timeout during high traffic",
            "severity": "P1",
            "category": "Networking"
        },
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    assert create_res.status_code == status.HTTP_201_CREATED
    inc_id = create_res.json()["id"]

    # Record a solution attempt
    att_res = client.post(
        f"/api/v1/incidents/{inc_id}/attempts",
        json={
            "solution_text": "Restarted API gateway worker processes",
            "outcome": "success"
        },
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    assert att_res.status_code == status.HTTP_201_CREATED

    # Retrieve metrics after resolution attempt
    res = client.get(
        "/api/v1/admin/dashboard",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    metrics = data["metrics"]
    sol_stats = data["solution_analytics"]

    assert metrics["total_incidents"] >= 1
    assert sol_stats["total_solution_attempts"] >= 1
    assert sol_stats["success_count"] >= 1

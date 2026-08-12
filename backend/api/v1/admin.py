"""Admin REST API endpoints for Dashboard Analytics and System Metrics."""

from fastapi import APIRouter, Depends, status
from backend.core.dependencies import get_admin_service
from backend.core.security import TokenData, require_role
from backend.schemas.admin import AdminDashboardResponse
from backend.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["Admin Analytics"])


@router.get("/dashboard", response_model=AdminDashboardResponse, status_code=status.HTTP_200_OK)
def get_admin_dashboard(
    current_token: TokenData = Depends(require_role(["admin"])),
    admin_service: AdminService = Depends(get_admin_service)
) -> AdminDashboardResponse:
    """
    Retrieve admin dashboard metrics and system analytics.
    
    AUTHENTICATION: Required (valid Bearer JWT).
    ROLE AUTHORIZATION: Admin only (role == "admin").
    EMPLOYEE ACCESS: Blocked with HTTP 403 Forbidden.
    """
    return admin_service.get_dashboard_metrics()


@router.get("/analytics", response_model=AdminDashboardResponse, status_code=status.HTTP_200_OK)
def get_admin_analytics(
    current_token: TokenData = Depends(require_role(["admin"])),
    admin_service: AdminService = Depends(get_admin_service)
) -> AdminDashboardResponse:
    """
    Retrieve detailed system analytics, solution success/failure rates, AI usage, and employee activity.
    
    AUTHENTICATION: Required (valid Bearer JWT).
    ROLE AUTHORIZATION: Admin only (role == "admin").
    EMPLOYEE ACCESS: Blocked with HTTP 403 Forbidden.
    """
    return admin_service.get_dashboard_metrics()

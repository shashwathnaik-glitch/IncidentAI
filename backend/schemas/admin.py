"""Pydantic schemas for Admin dashboard, system metrics, and analytics."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class SystemMetrics(BaseModel):
    """System-wide incident statistics."""
    total_incidents: int = 0
    active_incidents: int = 0
    open_incidents: int = 0
    investigating_incidents: int = 0
    resolved_incidents: int = 0
    closed_incidents: int = 0
    repeated_incidents: int = 0
    resolution_rate_pct: float = 0.0
    avg_mttr_minutes: float = 0.0


class SolutionAnalytics(BaseModel):
    """Solution attempt success and failure statistics."""
    total_solution_attempts: int = 0
    success_count: int = 0
    failure_count: int = 0
    partial_count: int = 0
    rejected_count: int = 0
    unknown_count: int = 0
    solution_success_rate_pct: float = 0.0


class EmployeeUsageAnalytics(BaseModel):
    """Employee activity and role statistics."""
    total_users: int = 2
    total_employees: int = 1
    total_admins: int = 1
    active_reporters_count: int = 0


class AIUsageAnalytics(BaseModel):
    """AI agent reasoning and approval statistics."""
    total_ai_analyses: int = 0
    total_action_approvals: int = 0
    avg_confidence_score: float = 0.85
    approval_rate_pct: float = 100.0


class SystemStatusInfo(BaseModel):
    """System status and component availability."""
    database_connected: bool = True
    ai_service_available: bool = True
    notifications_enabled: bool = True
    overall_status: str = "healthy"


class AdminDashboardResponse(BaseModel):
    """Response model for GET /api/v1/admin/dashboard and GET /api/v1/admin/analytics."""
    status: str = "active"
    metrics: SystemMetrics
    solution_analytics: SolutionAnalytics
    employee_usage: EmployeeUsageAnalytics
    ai_usage: AIUsageAnalytics
    system_status: SystemStatusInfo
    user_counts_by_role: Dict[str, int] = Field(default_factory=lambda: {"employee": 1, "admin": 1})

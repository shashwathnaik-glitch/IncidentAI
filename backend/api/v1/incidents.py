"""Incident REST API endpoints."""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from backend.core.dependencies import get_incident_service
from backend.core.security import TokenData, get_current_user_token
from backend.schemas.incident import (
    IncidentCreate,
    IncidentResponse,
    IncidentSeverityEnum,
    IncidentStatusEnum,
    IncidentUpdate,
    IncidentUpdateStatus,
    RepeatedIncidentAnalysis,
)
from backend.services.incident_service import IncidentService

router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
def create_incident(
    incident_create: IncidentCreate,
    current_token: TokenData = Depends(get_current_user_token),
    incident_service: IncidentService = Depends(get_incident_service)
) -> IncidentResponse:
    """
    Create a new incident report.
    Requires authentication.
    """
    reported_by = UUID(current_token.user_id)
    return incident_service.create_incident(incident_create, reported_by=reported_by)


@router.get("", response_model=List[IncidentResponse], status_code=status.HTTP_200_OK)
def list_incidents(
    status_filter: Optional[IncidentStatusEnum] = Query(None, alias="status", description="Filter by status"),
    severity_filter: Optional[IncidentSeverityEnum] = Query(None, alias="severity", description="Filter by severity"),
    category: Optional[str] = Query(None, description="Filter by category"),
    current_token: TokenData = Depends(get_current_user_token),
    incident_service: IncidentService = Depends(get_incident_service)
) -> List[IncidentResponse]:
    """
    List incidents with optional filters.
    Requires authentication.
    """
    return incident_service.list_incidents(
        status=status_filter,
        severity=severity_filter,
        category=category
    )


@router.get("/{id}", response_model=IncidentResponse, status_code=status.HTTP_200_OK)
def get_incident(
    id: UUID,
    current_token: TokenData = Depends(get_current_user_token),
    incident_service: IncidentService = Depends(get_incident_service)
) -> IncidentResponse:
    """
    Get detailed information for a single incident by ID.
    Requires authentication.
    """
    return incident_service.get_incident(incident_id=id)


@router.get("/{id}/repeated", response_model=RepeatedIncidentAnalysis, status_code=status.HTTP_200_OK)
def detect_repeated_incidents(
    id: UUID,
    current_token: TokenData = Depends(get_current_user_token),
    incident_service: IncidentService = Depends(get_incident_service)
) -> RepeatedIncidentAnalysis:
    """
    Analyze database records and memory references to detect repeated incident patterns.

    Returns: category, similar incident references, repeat count, recent occurrences,
    common solution attempts, and historical outcomes.
    Requires authentication.
    """
    return incident_service.detect_repeated_incidents(incident_id=id)


@router.put("/{id}", response_model=IncidentResponse, status_code=status.HTTP_200_OK)
def update_incident(
    id: UUID,
    incident_update: IncidentUpdate,
    current_token: TokenData = Depends(get_current_user_token),
    incident_service: IncidentService = Depends(get_incident_service)
) -> IncidentResponse:
    """
    Update incident fields (title, description, category, severity).
    Requires authentication.
    """
    return incident_service.update_incident(incident_id=id, update=incident_update)


@router.patch("/{id}/status", response_model=IncidentResponse, status_code=status.HTTP_200_OK)
def update_incident_status(
    id: UUID,
    status_update: IncidentUpdateStatus,
    current_token: TokenData = Depends(get_current_user_token),
    incident_service: IncidentService = Depends(get_incident_service)
) -> IncidentResponse:
    """
    Update status of an existing incident.
    Requires authentication.
    """
    return incident_service.update_incident_status(incident_id=id, new_status=status_update.status)

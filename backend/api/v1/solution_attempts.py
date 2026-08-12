"""Solution Attempt REST API endpoints."""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status
from backend.core.dependencies import get_solution_service
from backend.core.security import TokenData, get_current_user_token
from backend.schemas.solution_attempt import (
    SolutionAttemptCreate,
    SolutionAttemptResponse,
)
from backend.services.solution_service import SolutionService

router = APIRouter(prefix="/incidents", tags=["Solution Attempts"])


@router.post("/{id}/attempts", response_model=SolutionAttemptResponse, status_code=status.HTTP_201_CREATED)
def record_solution_attempt(
    id: UUID,
    attempt_create: SolutionAttemptCreate,
    current_token: TokenData = Depends(get_current_user_token),
    solution_service: SolutionService = Depends(get_solution_service)
) -> SolutionAttemptResponse:
    """
    Record a new solution attempt outcome for an incident.
    
    CRITICAL MEMORY RULE:
    Every call appends a NEW historical record. Past attempts are never overwritten or deleted.
    Allowed outcomes: success, failure, partial, rejected, unknown.
    Requires authentication.
    """
    performed_by = UUID(current_token.user_id)
    return solution_service.record_solution_attempt(
        incident_id=id,
        attempt_create=attempt_create,
        performed_by=performed_by
    )


@router.get("/{id}/attempts", response_model=List[SolutionAttemptResponse], status_code=status.HTTP_200_OK)
def list_solution_attempts(
    id: UUID,
    current_token: TokenData = Depends(get_current_user_token),
    solution_service: SolutionService = Depends(get_solution_service)
) -> List[SolutionAttemptResponse]:
    """
    Retrieve all historical solution attempts for an incident.
    Returns complete chronological history.
    Requires authentication.
    """
    return solution_service.get_solution_attempts(incident_id=id)

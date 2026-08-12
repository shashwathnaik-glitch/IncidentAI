"""AI Memory Search REST endpoint."""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from backend.core.dependencies import get_memory_service
from backend.core.security import TokenData, get_current_user_token
from backend.schemas.memory import MemorySearchQuery, MemorySearchResponse
from backend.services.memory_service import MemoryService

router = APIRouter(prefix="/memory", tags=["Memory"])


@router.get("/search", response_model=MemorySearchResponse, status_code=status.HTTP_200_OK)
def search_memory(
    q: str = Query(..., min_length=2, description="Search terms or incident symptom description"),
    category: Optional[str] = Query(None, description="Optional incident category filter"),
    severity: Optional[str] = Query(None, description="Optional severity filter"),
    limit: int = Query(default=5, ge=1, le=50, description="Max results limit"),
    current_token: TokenData = Depends(get_current_user_token),
    memory_service: MemoryService = Depends(get_memory_service)
) -> MemorySearchResponse:
    """
    Search historical incident memory using semantic search proxy.
    
    AUTHENTICATION: Required (valid Bearer JWT).
    OWNERSHIP: Backend validates request/response parameters and proxies through MemoryService.
    AI Agent engine performs semantic vector retrieval.
    """
    search_query = MemorySearchQuery(
        query=q,
        category=category,
        severity=severity,
        limit=limit
    )
    return memory_service.search_memory(search_query)

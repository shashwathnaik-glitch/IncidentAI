"""Pydantic schemas for AI memory search proxy requests and responses."""

from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class MemorySearchQuery(BaseModel):
    """Query parameters for GET /api/v1/memory/search."""
    query: str = Field(..., min_length=2, description="Search terms or incident symptom description")
    category: Optional[str] = Field(None, description="Optional incident category filter")
    severity: Optional[str] = Field(None, description="Optional severity filter (P1, P2, P3, P4)")
    limit: int = Field(default=5, ge=1, le=50, description="Max number of memory records to return")


class MemoryItemResponse(BaseModel):
    """Single historical memory record returned by AI memory search."""
    incident_id: UUID
    title: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    historical_outcomes: List[str] = Field(default_factory=list, description="Historical outcome list e.g. ['success', 'failure']")
    summary: str


class MemorySearchResponse(BaseModel):
    """Response payload for GET /api/v1/memory/search."""
    query: str
    total_results: int
    matches: List[MemoryItemResponse]

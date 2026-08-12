"""Pydantic schemas for Incident creation, retrieval, update, filtering, status management, and repeated incident detection."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class IncidentSeverityEnum(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class IncidentStatusEnum(str, Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"


class IncidentCreate(BaseModel):
    """Payload for POST /api/v1/incidents."""
    title: str = Field(..., min_length=3, max_length=200, json_schema_extra={"example": "Database connection pool exhausted"})
    description: str = Field(..., min_length=10, json_schema_extra={"example": "High traffic spike causing DB pool timeouts in production microservice"})
    category: str = Field(..., min_length=2, json_schema_extra={"example": "Database"})
    severity: IncidentSeverityEnum = Field(default=IncidentSeverityEnum.P3, json_schema_extra={"example": "P2"})


class IncidentUpdate(BaseModel):
    """Payload for PUT /api/v1/incidents/{id}."""
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, min_length=10)
    category: Optional[str] = Field(None, min_length=2)
    severity: Optional[IncidentSeverityEnum] = None


class IncidentUpdateStatus(BaseModel):
    """Payload for PATCH /api/v1/incidents/{id}/status."""
    status: IncidentStatusEnum = Field(..., json_schema_extra={"example": "investigating"})


class IncidentResponse(BaseModel):
    """Incident detail response model."""
    id: UUID
    title: str
    description: str
    category: str
    severity: IncidentSeverityEnum
    status: IncidentStatusEnum
    reported_by: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


class SimilarIncidentRef(BaseModel):
    """Reference summary model for a similar incident."""
    incident_id: UUID
    title: str
    similarity_score: float = 0.85
    status: str
    created_at: datetime


class RecentOccurrenceInfo(BaseModel):
    """Occurrence timestamp and summary info for repeated incidents."""
    incident_id: UUID
    title: str
    created_at: datetime


class RepeatedIncidentAnalysis(BaseModel):
    """Data and response model for repeated incident detection."""
    incident_id: UUID
    category: str
    repeat_count: int
    is_repeated_incident: bool
    similar_incident_references: List[SimilarIncidentRef]
    recent_occurrences: List[RecentOccurrenceInfo]
    common_solution_attempts: List[str]
    historical_outcomes: List[str]

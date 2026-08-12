"""Pydantic schemas for AI reasoning analysis and action approval contracts."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class HistoricalEvidence(BaseModel):
    """Historical solution attempt evidence summarized for AI recommendations."""
    successful_solutions: List[str] = Field(default_factory=list)
    failed_solutions: List[str] = Field(default_factory=list)


class AIAnalyzeRequest(BaseModel):
    """Payload for POST /api/v1/ai/analyze."""
    incident_id: UUID = Field(..., json_schema_extra={"example": "11111111-1111-1111-1111-111111111111"})
    error_logs: Optional[str] = Field(None, json_schema_extra={"example": "ConnectionTimeout: database host unreachable after 30000ms"})
    environment: Optional[str] = Field(default="production", json_schema_extra={"example": "production"})


class AIAnalyzeResponse(BaseModel):
    """Response payload for POST /api/v1/ai/analyze."""
    incident_id: UUID
    recommended_solution: str
    explanation: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    similar_incidents_found: int = 0
    historical_evidence: HistoricalEvidence
    risks: List[str] = Field(default_factory=list)
    requires_approval: bool = True
    action_id: Optional[str] = None


class AIApproveRequest(BaseModel):
    """Payload for POST /api/v1/ai/approve."""
    action_id: str = Field(..., json_schema_extra={"example": "ACT-98234-RESTART"})
    reasoning: Optional[str] = Field(None, json_schema_extra={"example": "Approved by engineer after reviewing risk assessment."})


class AIApproveResponse(BaseModel):
    """Response payload for POST /api/v1/ai/approve."""
    action_id: str
    status: str = "approved"
    approved_by: UUID
    approved_at: datetime

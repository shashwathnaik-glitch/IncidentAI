"""
Pydantic schemas for Solution Attempt outcome recording and historical log retrieval.

CRITICAL PRODUCT PRINCIPLE:
Every attempted solution receives an outcome (success/failure/partial/rejected/unknown).
Solution attempt records are IMMUTABLE. Historical outcomes are never deleted or overwritten.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class SolutionOutcomeEnum(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


class SolutionAttemptCreate(BaseModel):
    """Payload for POST /api/v1/incidents/{id}/attempts."""
    solution_text: str = Field(..., min_length=5, json_schema_extra={"example": "Increased DB max pool connections from 20 to 100"})
    outcome: SolutionOutcomeEnum = Field(..., json_schema_extra={"example": "success"})
    failure_reason: Optional[str] = Field(None, json_schema_extra={"example": "Connection limit reached downstream DB host"})
    execution_duration_ms: Optional[int] = Field(default=0, ge=0, json_schema_extra={"example": 450})
    confidence_at_execution: Optional[float] = Field(default=0.0, ge=0.0, le=1.0, json_schema_extra={"example": 0.85})
    reward_info: Optional[float] = Field(default=None, json_schema_extra={"example": 1.0})


class SolutionAttemptResponse(BaseModel):
    """Historical solution attempt response model."""
    id: UUID
    incident_id: UUID
    solution_text: str
    outcome: SolutionOutcomeEnum
    failure_reason: Optional[str] = None
    performed_by: UUID
    execution_duration_ms: int = 0
    confidence_at_execution: float = 0.0
    reward_info: Optional[float] = None
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

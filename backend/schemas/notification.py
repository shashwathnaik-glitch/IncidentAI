"""Pydantic schemas for Notification events and dispatch contracts."""

from enum import Enum
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class NotificationEventTypeEnum(str, Enum):
    NEW_INCIDENT = "new_incident"
    CRITICAL_INCIDENT = "critical_incident"
    AI_RECOMMENDATION = "ai_recommendation"
    RESOLUTION_COMPLETED = "resolution_completed"
    REPEATED_INCIDENT_DETECTED = "repeated_incident_detected"


class NotificationSendRequest(BaseModel):
    """Payload for POST /api/v1/notifications/send."""
    event_type: NotificationEventTypeEnum = Field(..., json_schema_extra={"example": "critical_incident"})
    incident_id: Optional[UUID] = Field(None, json_schema_extra={"example": "11111111-1111-1111-1111-111111111111"})
    title: str = Field(..., min_length=3, json_schema_extra={"example": "Database Connection Timeout P1"})
    message: str = Field(..., min_length=5, json_schema_extra={"example": "P1 critical incident reported on production database cluster."})
    recipient_email: Optional[str] = Field(None, json_schema_extra={"example": "oncall@company.com"})
    slack_channel: Optional[str] = Field(None, json_schema_extra={"example": "#critical-alerts"})


class NotificationResponse(BaseModel):
    """Response payload for notification dispatch."""
    success: bool
    event_type: NotificationEventTypeEnum
    email_sent: bool = False
    slack_sent: bool = False
    details: str

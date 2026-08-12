"""Notification REST API endpoints."""

from fastapi import APIRouter, Depends, status
from backend.core.dependencies import get_notification_service
from backend.core.security import TokenData, get_current_user_token
from backend.schemas.notification import (
    NotificationSendRequest,
    NotificationResponse,
)
from backend.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.post("/send", response_model=NotificationResponse, status_code=status.HTTP_200_OK)
def send_notification(
    request: NotificationSendRequest,
    current_token: TokenData = Depends(get_current_user_token),
    notification_service: NotificationService = Depends(get_notification_service)
) -> NotificationResponse:
    """
    Dispatch an Email and/or Slack notification for an incident event.
    
    EVENTS:
    - new_incident
    - critical_incident
    - ai_recommendation
    - resolution_completed
    - repeated_incident_detected
    
    AUTHENTICATION: Required (valid Bearer JWT).
    """
    return notification_service.notify(request)

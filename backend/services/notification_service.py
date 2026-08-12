"""
Service layer for Incident Notification alerting.

ARCHITECTURE PATTERN:
API Route / Services -> NotificationService (services/notification_service.py) -> INotificationInterface (interfaces/notification_interface.py)

CRITICAL RESILIENCE RULE:
Notification failures MUST NEVER crash the main incident workflow.
All transport calls are wrapped safely, logging warnings on transport error without raising unhandled exceptions.
"""

from typing import Dict, Any, Optional
from backend.core.config import settings
from backend.core.logging import logger
from backend.interfaces.notification_interface import INotificationInterface
from backend.schemas.notification import (
    NotificationEventTypeEnum,
    NotificationSendRequest,
    NotificationResponse,
)


class NotificationService:
    def __init__(self, notification_interface: INotificationInterface):
        self.notification_interface = notification_interface

    def _format_event_message(self, event_type: NotificationEventTypeEnum, title: str, details: str) -> Dict[str, str]:
        """Format email subject, body, and Slack message based on event type."""
        prefix_map = {
            NotificationEventTypeEnum.NEW_INCIDENT: "[NEW INCIDENT REPORTED]",
            NotificationEventTypeEnum.CRITICAL_INCIDENT: "[CRITICAL P1/P2 ALERT]",
            NotificationEventTypeEnum.AI_RECOMMENDATION: "[AI RECOMMENDATION READY]",
            NotificationEventTypeEnum.RESOLUTION_COMPLETED: "[INCIDENT RESOLVED]",
            NotificationEventTypeEnum.REPEATED_INCIDENT_DETECTED: "[REPEATED INCIDENT DETECTED]",
        }
        
        tag = prefix_map.get(event_type, "[INCIDENT ALERT]")
        subject = f"{tag} {title}"
        body = f"Incident Notification Event: {event_type.value.upper()}\nTitle: {title}\nDetails: {details}\nTimestamp: Auto-generated"
        slack_msg = f"*{tag}* `{title}`\n>{details}"
        
        return {
            "subject": subject,
            "body": body,
            "slack": slack_msg
        }

    def notify(self, request: NotificationSendRequest) -> NotificationResponse:
        """
        Dispatch notification for an event.
        
        RESILIENCE GUARANTEE:
        Catches any transport errors safely without raising exceptions.
        """
        if not settings.NOTIFICATIONS_ENABLED:
            logger.info("[NOTIFICATIONS DISABLED] Global notifications toggle is off.")
            return NotificationResponse(
                success=True,
                event_type=request.event_type,
                email_sent=False,
                slack_sent=False,
                details="Notifications globally disabled"
            )

        formatted = self._format_event_message(request.event_type, request.title, request.message)

        email_recipient = request.recipient_email or settings.SMTP_FROM_EMAIL
        slack_chan = request.slack_channel or settings.SLACK_DEFAULT_CHANNEL

        email_success = False
        slack_success = False

        # 1. Attempt Email dispatch safely
        try:
            email_success = self.notification_interface.send_email_notification(
                recipient=email_recipient,
                subject=formatted["subject"],
                body=formatted["body"]
            )
        except Exception as err:
            logger.warning(f"[SAFE FALLBACK] Email dispatch exception suppressed safely: {type(err).__name__}")

        # 2. Attempt Slack dispatch safely
        try:
            slack_success = self.notification_interface.send_slack_notification(
                channel=slack_chan,
                message=formatted["slack"]
            )
        except Exception as err:
            logger.warning(f"[SAFE FALLBACK] Slack dispatch exception suppressed safely: {type(err).__name__}")

        return NotificationResponse(
            success=(email_success or slack_success),
            event_type=request.event_type,
            email_sent=email_success,
            slack_sent=slack_success,
            details=f"Email sent: {email_success}, Slack sent: {slack_success}"
        )

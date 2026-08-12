"""Dedicated unit and integration tests for Notification Service and API endpoint."""

from unittest.mock import MagicMock
from fastapi import status
from backend.schemas.notification import NotificationEventTypeEnum, NotificationSendRequest
from backend.services.notification_service import NotificationService


def get_auth_token(client, email="employee@company.com", password="Password123!"):
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password}
    )
    return login_res.json()["access_token"]


def test_notification_send_endpoint_unauthenticated(client):
    """Verify POST /api/v1/notifications/send requires valid authentication."""
    res = client.post(
        "/api/v1/notifications/send",
        json={
            "event_type": "critical_incident",
            "title": "Database Failure",
            "message": "P1 critical database node offline"
        }
    )
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


def test_notification_send_endpoint_success(client):
    """Verify POST /api/v1/notifications/send dispatches notifications for authenticated user."""
    token = get_auth_token(client)
    res = client.post(
        "/api/v1/notifications/send",
        json={
            "event_type": "new_incident",
            "title": "API Gateway Timeout",
            "message": "New P2 incident reported on auth service",
            "recipient_email": "oncall@company.com",
            "slack_channel": "#incidents-alerts"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["success"] is True
    assert data["event_type"] == "new_incident"
    assert data["email_sent"] is True
    assert data["slack_sent"] is True


def test_all_notification_event_types_formatting():
    """Verify notification message formatting for all 5 supported event types."""
    mock_interface = MagicMock()
    mock_interface.send_email_notification.return_value = True
    mock_interface.send_slack_notification.return_value = True

    service = NotificationService(notification_interface=mock_interface)

    events = [
        NotificationEventTypeEnum.NEW_INCIDENT,
        NotificationEventTypeEnum.CRITICAL_INCIDENT,
        NotificationEventTypeEnum.AI_RECOMMENDATION,
        NotificationEventTypeEnum.RESOLUTION_COMPLETED,
        NotificationEventTypeEnum.REPEATED_INCIDENT_DETECTED,
    ]

    for event_type in events:
        req = NotificationSendRequest(
            event_type=event_type,
            title=f"Test Event {event_type.value}",
            message="Test message details"
        )
        res = service.notify(req)
        assert res.success is True
        assert res.event_type == event_type


def test_safe_exception_suppression_on_transport_failure():
    """
    CRITICAL RESILIENCE TEST:
    Verify that transport exception during notification dispatch does NOT crash the service or workflow.
    The service must catch transport errors safely and return success=False without raising.
    """
    failing_interface = MagicMock()
    failing_interface.send_email_notification.side_effect = Exception("SMTP Connection Refused")
    failing_interface.send_slack_notification.side_effect = Exception("Slack Timeout")

    service = NotificationService(notification_interface=failing_interface)
    req = NotificationSendRequest(
        event_type=NotificationEventTypeEnum.CRITICAL_INCIDENT,
        title="Safe Fallback Test",
        message="This transport failure must not crash main workflow"
    )

    # Must NOT raise exception
    res = service.notify(req)
    assert res.success is False
    assert res.email_sent is False
    assert res.slack_sent is False

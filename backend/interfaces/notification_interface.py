"""
Abstract Notification Service Interface.

Interface contract for Email and Slack alert services.
"""

from abc import ABC, abstractmethod


class INotificationInterface(ABC):
    """Interface contract for dispatching incident notification alerts."""

    @abstractmethod
    def send_email_notification(self, recipient: str, subject: str, body: str) -> bool:
        """Send an email notification via SMTP/SES."""
        pass

    @abstractmethod
    def send_slack_notification(self, channel: str, message: str) -> bool:
        """Send a Slack notification via webhook or Slack API."""
        pass

"""
Notification transport implementations for Email (SMTP) and Slack Webhook delivery.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import httpx
from backend.core.config import settings
from backend.core.logging import logger
from backend.interfaces.notification_interface import INotificationInterface


class ConsoleNotificationInterface(INotificationInterface):
    """
    Console/Logger transport implementation.
    Used during testing or when external email/Slack credentials are not configured.
    """

    def send_email_notification(self, recipient: str, subject: str, body: str) -> bool:
        logger.info(f"[CONSOLE EMAIL ALERT] To: {recipient} | Subject: {subject} | Body: {body}")
        return True

    def send_slack_notification(self, channel: str, message: str) -> bool:
        logger.info(f"[CONSOLE SLACK ALERT] Channel: {channel} | Message: {message}")
        return True


class SMTPAndSlackNotificationInterface(INotificationInterface):
    """
    Production Email (SMTP) and Slack Webhook transport implementation.
    Falls back safely with logged warnings if credentials or webhook URLs are not configured.
    """

    def send_email_notification(self, recipient: str, subject: str, body: str) -> bool:
        if not settings.SMTP_HOST or not settings.SMTP_USER:
            logger.warning(f"[EMAIL DISPATCH SKIPPED] SMTP host/user not configured. Message for '{recipient}' logged locally.")
            return False

        try:
            msg = MIMEMultipart()
            msg["From"] = settings.SMTP_FROM_EMAIL
            msg["To"] = recipient
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            
            logger.info(f"[EMAIL SENT] Successfully dispatched email to {recipient}")
            return True
        except Exception as err:
            logger.warning(f"[EMAIL DELIVERY FAILED] Transport error sending to '{recipient}': {type(err).__name__}")
            return False

    def send_slack_notification(self, channel: str, message: str) -> bool:
        webhook_url = settings.SLACK_WEBHOOK_URL
        if not webhook_url:
            logger.warning(f"[SLACK DISPATCH SKIPPED] SLACK_WEBHOOK_URL not configured. Message for '{channel}' logged locally.")
            return False

        try:
            payload = {
                "channel": channel or settings.SLACK_DEFAULT_CHANNEL,
                "text": message
            }
            with httpx.Client(timeout=10.0) as client:
                res = client.post(webhook_url, json=payload)
                if res.status_code == 200:
                    logger.info(f"[SLACK SENT] Successfully dispatched webhook to channel {channel}")
                    return True
                else:
                    logger.warning(f"[SLACK DELIVERY FAILED] Webhook returned status code {res.status_code}")
                    return False
        except Exception as err:
            logger.warning(f"[SLACK DELIVERY FAILED] Transport error dispatching to channel '{channel}': {type(err).__name__}")
            return False

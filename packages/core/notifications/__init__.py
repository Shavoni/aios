"""Notification Service for aiOS.

Handles multi-channel notification delivery:
- Email (via SMTP or SendGrid, or dev mode file logging)
- Push notifications (via Firebase/OneSignal)
- In-app notifications (stored in workflow manager)

Integrates with:
- HITL workflow notifications
- User notification preferences
- SLA warnings and escalations

DEV MODE:
When AIOS_NOTIFICATION_MODE=development (default), emails are logged to
data/notifications/ instead of being sent. This allows full testing without
email configuration.
"""

from __future__ import annotations

import os
import json
import smtplib
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from enum import Enum
from pathlib import Path
from typing import Any, Callable
import logging

logger = logging.getLogger(__name__)

# Dev mode: log to files instead of sending
NOTIFICATION_MODE = os.getenv("AIOS_NOTIFICATION_MODE", "development")
NOTIFICATION_LOG_PATH = Path(os.getenv("AIOS_NOTIFICATION_LOG_PATH", "data/notifications"))


class NotificationChannel(str, Enum):
    """Available notification channels."""
    EMAIL = "email"
    PUSH = "push"
    IN_APP = "in_app"


class NotificationPriority(str, Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class NotificationPayload:
    """Payload for a notification."""

    id: str
    type: str  # escalation, draft_pending, policy_change, sla_warning, etc.
    recipient_id: str
    recipient_email: str | None = None
    title: str = ""
    message: str = ""
    html_message: str | None = None
    priority: NotificationPriority = NotificationPriority.NORMAL
    channels: list[NotificationChannel] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # Tracking
    sent_channels: list[NotificationChannel] = field(default_factory=list)
    failed_channels: list[NotificationChannel] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)


class NotificationAdapter(ABC):
    """Base class for notification channel adapters."""

    @property
    @abstractmethod
    def channel(self) -> NotificationChannel:
        """Return the channel this adapter handles."""
        pass

    @abstractmethod
    async def send(self, payload: NotificationPayload) -> bool:
        """Send notification. Returns True if successful."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the adapter is properly configured and working."""
        pass


class EmailAdapter(NotificationAdapter):
    """Email notification adapter supporting SMTP, SendGrid, and dev mode file logging."""

    def __init__(self):
        # Dev mode check
        self.dev_mode = NOTIFICATION_MODE == "development"

        # SMTP settings from environment
        self.smtp_host = os.getenv("AIOS_SMTP_HOST", "")
        self.smtp_port = int(os.getenv("AIOS_SMTP_PORT", "587"))
        self.smtp_user = os.getenv("AIOS_SMTP_USER", "")
        self.smtp_password = os.getenv("AIOS_SMTP_PASSWORD", "")
        self.smtp_from = os.getenv("AIOS_SMTP_FROM", "noreply@haais.ai")
        self.smtp_tls = os.getenv("AIOS_SMTP_TLS", "true").lower() == "true"

        # SendGrid as alternative
        self.sendgrid_api_key = os.getenv("SENDGRID_API_KEY", "")

        # Template settings
        self.org_name = os.getenv("AIOS_ORG_NAME", "HAAIS AIOS")

        # Ensure dev log path exists
        if self.dev_mode:
            NOTIFICATION_LOG_PATH.mkdir(parents=True, exist_ok=True)
            (NOTIFICATION_LOG_PATH / "emails").mkdir(exist_ok=True)

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.EMAIL

    def _is_configured(self) -> bool:
        """Check if email is configured."""
        # Dev mode is always "configured"
        if self.dev_mode:
            return True
        return bool(self.smtp_host and self.smtp_user) or bool(self.sendgrid_api_key)

    async def health_check(self) -> bool:
        """Check email configuration."""
        # Dev mode is always healthy
        if self.dev_mode:
            logger.info("Email adapter running in DEVELOPMENT mode - emails logged to files")
            return True

        if not self._is_configured():
            logger.warning("Email notifications not configured. Set AIOS_SMTP_* or SENDGRID_API_KEY env vars.")
            return False

        if self.sendgrid_api_key:
            return True  # Assume SendGrid is working if API key is set

        # Test SMTP connection
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._test_smtp_connection)
        except Exception as e:
            logger.error(f"SMTP health check failed: {e}")
            return False

    def _test_smtp_connection(self) -> bool:
        """Test SMTP connection (sync)."""
        try:
            if self.smtp_tls:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10)
                server.starttls()
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10)

            if self.smtp_user and self.smtp_password:
                server.login(self.smtp_user, self.smtp_password)

            server.quit()
            return True
        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}")
            return False

    async def send(self, payload: NotificationPayload) -> bool:
        """Send email notification."""
        # Dev mode: log to file instead of sending
        if self.dev_mode:
            return await self._send_dev_mode(payload)

        if not payload.recipient_email:
            logger.warning(f"No email address for recipient {payload.recipient_id}")
            payload.errors["email"] = "No recipient email address"
            return False

        if not self._is_configured():
            logger.warning("Email not configured, skipping email notification")
            payload.errors["email"] = "Email service not configured"
            return False

        # Use SendGrid if available, otherwise SMTP
        if self.sendgrid_api_key:
            return await self._send_via_sendgrid(payload)
        else:
            return await self._send_via_smtp(payload)

    async def _send_dev_mode(self, payload: NotificationPayload) -> bool:
        """Log email to file in development mode."""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{payload.id[:8]}.json"
            filepath = NOTIFICATION_LOG_PATH / "emails" / filename

            email_data = {
                "id": payload.id,
                "type": payload.type,
                "to": payload.recipient_email or f"{payload.recipient_id}@example.com",
                "from": self.smtp_from,
                "subject": f"[{self.org_name}] {payload.title}",
                "body_text": payload.message,
                "body_html": payload.html_message or self._generate_html_email(payload),
                "priority": payload.priority.value,
                "metadata": payload.metadata,
                "created_at": payload.created_at,
                "logged_at": datetime.utcnow().isoformat(),
                "mode": "development",
            }

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(email_data, f, indent=2, default=str)

            logger.info(f"[DEV MODE] Email logged to {filepath}")
            return True

        except Exception as e:
            logger.error(f"Failed to log email in dev mode: {e}")
            payload.errors["email"] = str(e)
            return False

    async def _send_via_smtp(self, payload: NotificationPayload) -> bool:
        """Send via SMTP."""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[{self.org_name}] {payload.title}"
            msg["From"] = self.smtp_from
            msg["To"] = payload.recipient_email

            # Add priority headers for urgent messages
            if payload.priority == NotificationPriority.URGENT:
                msg["X-Priority"] = "1"
                msg["X-MSMail-Priority"] = "High"

            # Plain text version
            text_part = MIMEText(payload.message, "plain")
            msg.attach(text_part)

            # HTML version if available
            if payload.html_message:
                html_part = MIMEText(payload.html_message, "html")
                msg.attach(html_part)
            else:
                # Generate simple HTML from plain text
                html_content = self._generate_html_email(payload)
                html_part = MIMEText(html_content, "html")
                msg.attach(html_part)

            # Send in executor to not block
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._smtp_send, msg)

            logger.info(f"Email sent to {payload.recipient_email}: {payload.title}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            payload.errors["email"] = str(e)
            return False

    def _smtp_send(self, msg: MIMEMultipart) -> None:
        """Synchronous SMTP send."""
        if self.smtp_tls:
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
        else:
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)

        if self.smtp_user and self.smtp_password:
            server.login(self.smtp_user, self.smtp_password)

        server.send_message(msg)
        server.quit()

    async def _send_via_sendgrid(self, payload: NotificationPayload) -> bool:
        """Send via SendGrid API."""
        try:
            import httpx

            html_content = payload.html_message or self._generate_html_email(payload)

            data = {
                "personalizations": [{
                    "to": [{"email": payload.recipient_email}],
                    "subject": f"[{self.org_name}] {payload.title}",
                }],
                "from": {"email": self.smtp_from, "name": self.org_name},
                "content": [
                    {"type": "text/plain", "value": payload.message},
                    {"type": "text/html", "value": html_content},
                ],
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    json=data,
                    headers={
                        "Authorization": f"Bearer {self.sendgrid_api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=30.0,
                )

                if response.status_code in (200, 201, 202):
                    logger.info(f"SendGrid email sent to {payload.recipient_email}")
                    return True
                else:
                    logger.error(f"SendGrid error: {response.status_code} - {response.text}")
                    payload.errors["email"] = f"SendGrid error: {response.status_code}"
                    return False

        except ImportError:
            logger.error("httpx not installed, cannot use SendGrid")
            payload.errors["email"] = "httpx not installed"
            return False
        except Exception as e:
            logger.error(f"SendGrid send failed: {e}")
            payload.errors["email"] = str(e)
            return False

    def _generate_html_email(self, payload: NotificationPayload) -> str:
        """Generate HTML email from payload."""
        priority_color = {
            NotificationPriority.LOW: "#6c757d",
            NotificationPriority.NORMAL: "#0d6efd",
            NotificationPriority.HIGH: "#fd7e14",
            NotificationPriority.URGENT: "#dc3545",
        }.get(payload.priority, "#0d6efd")

        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f8f9fa; padding: 20px; border: 1px solid #dee2e6; border-top: none; }}
        .priority-badge {{ display: inline-block; padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: bold; color: white; background: {priority_color}; }}
        .footer {{ text-align: center; color: #6c757d; font-size: 12px; margin-top: 20px; }}
        .button {{ display: inline-block; padding: 12px 24px; background: #667eea; color: white; text-decoration: none; border-radius: 6px; margin-top: 16px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2 style="margin:0;">{self.org_name}</h2>
            <p style="margin:8px 0 0 0; opacity:0.9;">{payload.type.replace('_', ' ').title()}</p>
        </div>
        <div class="content">
            <span class="priority-badge">{payload.priority.value.upper()}</span>
            <h3>{payload.title}</h3>
            <p>{payload.message.replace(chr(10), '<br>')}</p>
            <a href="#" class="button">View in Dashboard</a>
        </div>
        <div class="footer">
            <p>This is an automated message from {self.org_name}.</p>
            <p>To manage your notification preferences, visit your settings.</p>
        </div>
    </div>
</body>
</html>
"""


class PushAdapter(NotificationAdapter):
    """Push notification adapter supporting Firebase, OneSignal, and dev mode file logging."""

    def __init__(self):
        self.dev_mode = NOTIFICATION_MODE == "development"
        self.firebase_key = os.getenv("FIREBASE_SERVER_KEY", "")
        self.onesignal_app_id = os.getenv("ONESIGNAL_APP_ID", "")
        self.onesignal_api_key = os.getenv("ONESIGNAL_API_KEY", "")

        # Ensure dev log path exists
        if self.dev_mode:
            NOTIFICATION_LOG_PATH.mkdir(parents=True, exist_ok=True)
            (NOTIFICATION_LOG_PATH / "push").mkdir(exist_ok=True)

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.PUSH

    def _is_configured(self) -> bool:
        if self.dev_mode:
            return True
        return bool(self.firebase_key) or bool(self.onesignal_app_id and self.onesignal_api_key)

    async def health_check(self) -> bool:
        if self.dev_mode:
            logger.info("Push adapter running in DEVELOPMENT mode - notifications logged to files")
            return True

        if not self._is_configured():
            logger.warning("Push notifications not configured. Set FIREBASE_SERVER_KEY or ONESIGNAL_* env vars.")
            return False
        return True

    async def send(self, payload: NotificationPayload) -> bool:
        """Send push notification."""
        # Dev mode: log to file
        if self.dev_mode:
            return await self._send_dev_mode(payload)

        if not self._is_configured():
            logger.debug("Push not configured, skipping")
            payload.errors["push"] = "Push service not configured"
            return False

        # Prefer OneSignal, fallback to Firebase
        if self.onesignal_app_id:
            return await self._send_via_onesignal(payload)
        else:
            return await self._send_via_firebase(payload)

    async def _send_dev_mode(self, payload: NotificationPayload) -> bool:
        """Log push notification to file in development mode."""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{payload.id[:8]}.json"
            filepath = NOTIFICATION_LOG_PATH / "push" / filename

            push_data = {
                "id": payload.id,
                "type": payload.type,
                "recipient_id": payload.recipient_id,
                "title": payload.title,
                "body": payload.message,
                "priority": payload.priority.value,
                "metadata": payload.metadata,
                "created_at": payload.created_at,
                "logged_at": datetime.utcnow().isoformat(),
                "mode": "development",
            }

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(push_data, f, indent=2, default=str)

            logger.info(f"[DEV MODE] Push notification logged to {filepath}")
            return True

        except Exception as e:
            logger.error(f"Failed to log push in dev mode: {e}")
            payload.errors["push"] = str(e)
            return False

    async def _send_via_onesignal(self, payload: NotificationPayload) -> bool:
        """Send via OneSignal."""
        try:
            import httpx

            data = {
                "app_id": self.onesignal_app_id,
                "include_external_user_ids": [payload.recipient_id],
                "headings": {"en": payload.title},
                "contents": {"en": payload.message},
                "data": payload.metadata,
            }

            # Add priority for urgent notifications
            if payload.priority == NotificationPriority.URGENT:
                data["priority"] = 10

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://onesignal.com/api/v1/notifications",
                    json=data,
                    headers={
                        "Authorization": f"Basic {self.onesignal_api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=30.0,
                )

                if response.status_code == 200:
                    logger.info(f"Push sent to {payload.recipient_id}")
                    return True
                else:
                    logger.error(f"OneSignal error: {response.text}")
                    payload.errors["push"] = f"OneSignal error: {response.status_code}"
                    return False

        except ImportError:
            payload.errors["push"] = "httpx not installed"
            return False
        except Exception as e:
            logger.error(f"Push send failed: {e}")
            payload.errors["push"] = str(e)
            return False

    async def _send_via_firebase(self, payload: NotificationPayload) -> bool:
        """Send via Firebase Cloud Messaging."""
        try:
            import httpx

            # Get device token from metadata
            device_token = payload.metadata.get("device_token")
            if not device_token:
                payload.errors["push"] = "No device token"
                return False

            data = {
                "to": device_token,
                "notification": {
                    "title": payload.title,
                    "body": payload.message,
                },
                "data": payload.metadata,
            }

            if payload.priority == NotificationPriority.URGENT:
                data["priority"] = "high"

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://fcm.googleapis.com/fcm/send",
                    json=data,
                    headers={
                        "Authorization": f"key={self.firebase_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=30.0,
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("success", 0) > 0:
                        logger.info(f"Firebase push sent to {payload.recipient_id}")
                        return True
                    else:
                        payload.errors["push"] = "FCM delivery failed"
                        return False
                else:
                    payload.errors["push"] = f"FCM error: {response.status_code}"
                    return False

        except ImportError:
            payload.errors["push"] = "httpx not installed"
            return False
        except Exception as e:
            payload.errors["push"] = str(e)
            return False


class InAppAdapter(NotificationAdapter):
    """In-app notification adapter (stores in workflow manager)."""

    def __init__(self):
        self._notifications: list[NotificationPayload] = []
        self._handlers: list[Callable[[NotificationPayload], None]] = []

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.IN_APP

    async def health_check(self) -> bool:
        return True  # Always available

    async def send(self, payload: NotificationPayload) -> bool:
        """Store in-app notification."""
        self._notifications.append(payload)

        # Call registered handlers
        for handler in self._handlers:
            try:
                handler(payload)
            except Exception as e:
                logger.error(f"Notification handler error: {e}")

        logger.info(f"In-app notification stored for {payload.recipient_id}")
        return True

    def register_handler(self, handler: Callable[[NotificationPayload], None]) -> None:
        """Register a handler for in-app notifications."""
        self._handlers.append(handler)

    def get_notifications(
        self,
        recipient_id: str,
        limit: int = 50,
    ) -> list[NotificationPayload]:
        """Get in-app notifications for a recipient."""
        return [
            n for n in self._notifications
            if n.recipient_id == recipient_id
        ][-limit:]


class NotificationService:
    """Central notification service that dispatches to channels based on preferences."""

    _instance: NotificationService | None = None

    def __init__(self):
        self._adapters: dict[NotificationChannel, NotificationAdapter] = {
            NotificationChannel.EMAIL: EmailAdapter(),
            NotificationChannel.PUSH: PushAdapter(),
            NotificationChannel.IN_APP: InAppAdapter(),
        }

        # User email lookup (should integrate with auth/user service)
        self._user_emails: dict[str, str] = {}

        # Notification preferences lookup
        self._preferences_lookup: Callable[[str], dict] | None = None

    @classmethod
    def get_instance(cls) -> NotificationService:
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None

    def set_user_email(self, user_id: str, email: str) -> None:
        """Register a user's email address."""
        self._user_emails[user_id] = email

    def set_preferences_lookup(self, lookup: Callable[[str], dict]) -> None:
        """Set a function to look up user notification preferences."""
        self._preferences_lookup = lookup

    def get_adapter(self, channel: NotificationChannel) -> NotificationAdapter:
        """Get adapter for a channel."""
        return self._adapters[channel]

    async def health_check(self) -> dict[str, bool]:
        """Check health of all notification channels."""
        results = {}
        for channel, adapter in self._adapters.items():
            results[channel.value] = await adapter.health_check()
        return results

    def _get_user_preferences(self, user_id: str, notification_type: str) -> dict[str, bool]:
        """Get user's notification preferences for a type."""
        # Default preferences
        defaults = {
            "escalation_alerts": {"email": True, "push": True, "in_app": True},
            "draft_pending": {"email": False, "push": True, "in_app": True},
            "policy_changes": {"email": True, "push": False, "in_app": True},
            "sla_warnings": {"email": True, "push": True, "in_app": True},
            "weekly_summary": {"email": False, "push": False, "in_app": False},
        }

        if self._preferences_lookup:
            try:
                prefs = self._preferences_lookup(user_id)
                type_prefs = prefs.get(notification_type, {})
                return {
                    "email": type_prefs.get("email", defaults.get(notification_type, {}).get("email", True)),
                    "push": type_prefs.get("push", defaults.get(notification_type, {}).get("push", True)),
                    "in_app": type_prefs.get("in_app", defaults.get(notification_type, {}).get("in_app", True)),
                }
            except Exception:
                pass

        return defaults.get(notification_type, {"email": True, "push": True, "in_app": True})

    async def send(
        self,
        notification_type: str,
        recipient_id: str,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        metadata: dict[str, Any] | None = None,
        html_message: str | None = None,
        force_channels: list[NotificationChannel] | None = None,
    ) -> NotificationPayload:
        """Send a notification through appropriate channels.

        Args:
            notification_type: Type of notification (escalation_alerts, draft_pending, etc.)
            recipient_id: User ID of recipient
            title: Notification title
            message: Notification message
            priority: Priority level
            metadata: Additional data
            html_message: Optional HTML version of message
            force_channels: Override user preferences with specific channels

        Returns:
            NotificationPayload with delivery status
        """
        import uuid

        # Get user's email if available
        recipient_email = self._user_emails.get(recipient_id)

        # Determine which channels to use
        if force_channels:
            channels = force_channels
        else:
            prefs = self._get_user_preferences(recipient_id, notification_type)
            channels = []
            if prefs.get("email"):
                channels.append(NotificationChannel.EMAIL)
            if prefs.get("push"):
                channels.append(NotificationChannel.PUSH)
            if prefs.get("in_app"):
                channels.append(NotificationChannel.IN_APP)

        payload = NotificationPayload(
            id=str(uuid.uuid4()),
            type=notification_type,
            recipient_id=recipient_id,
            recipient_email=recipient_email,
            title=title,
            message=message,
            html_message=html_message,
            priority=priority,
            channels=channels,
            metadata=metadata or {},
        )

        # Send to each channel
        for channel in channels:
            adapter = self._adapters.get(channel)
            if adapter:
                try:
                    success = await adapter.send(payload)
                    if success:
                        payload.sent_channels.append(channel)
                    else:
                        payload.failed_channels.append(channel)
                except Exception as e:
                    logger.error(f"Failed to send {channel.value}: {e}")
                    payload.failed_channels.append(channel)
                    payload.errors[channel.value] = str(e)

        return payload

    async def send_escalation_alert(
        self,
        recipient_id: str,
        approval_id: str,
        agent_name: str,
        escalation_reason: str,
        original_query: str,
    ) -> NotificationPayload:
        """Send escalation alert notification."""
        return await self.send(
            notification_type="escalation_alerts",
            recipient_id=recipient_id,
            title=f"Escalation Required: {agent_name}",
            message=f"A request has been escalated for your review.\n\nReason: {escalation_reason}\n\nOriginal Query: {original_query[:200]}...",
            priority=NotificationPriority.URGENT,
            metadata={
                "approval_id": approval_id,
                "agent_name": agent_name,
            },
        )

    async def send_draft_pending(
        self,
        recipient_id: str,
        approval_id: str,
        agent_name: str,
        draft_preview: str,
    ) -> NotificationPayload:
        """Send draft pending notification."""
        return await self.send(
            notification_type="draft_pending",
            recipient_id=recipient_id,
            title=f"Draft Awaiting Review: {agent_name}",
            message=f"A draft response is awaiting your review.\n\nPreview: {draft_preview[:200]}...",
            priority=NotificationPriority.NORMAL,
            metadata={
                "approval_id": approval_id,
                "agent_name": agent_name,
            },
        )

    async def send_sla_warning(
        self,
        recipient_id: str,
        approval_id: str,
        time_remaining_minutes: int,
    ) -> NotificationPayload:
        """Send SLA warning notification."""
        return await self.send(
            notification_type="sla_warnings",
            recipient_id=recipient_id,
            title="SLA Warning: Approval Deadline Approaching",
            message=f"An approval request is approaching its SLA deadline. Time remaining: {time_remaining_minutes} minutes.",
            priority=NotificationPriority.HIGH,
            metadata={
                "approval_id": approval_id,
                "time_remaining_minutes": time_remaining_minutes,
            },
        )

    async def send_policy_change(
        self,
        recipient_id: str,
        policy_name: str,
        change_type: str,
        changed_by: str,
    ) -> NotificationPayload:
        """Send policy change notification."""
        return await self.send(
            notification_type="policy_changes",
            recipient_id=recipient_id,
            title=f"Policy {change_type.title()}: {policy_name}",
            message=f"A governance policy has been {change_type}.\n\nPolicy: {policy_name}\nChanged by: {changed_by}",
            priority=NotificationPriority.NORMAL,
            metadata={
                "policy_name": policy_name,
                "change_type": change_type,
                "changed_by": changed_by,
            },
        )


def get_notification_service() -> NotificationService:
    """Get the notification service singleton."""
    return NotificationService.get_instance()


# Integration helper to connect with HITL workflow
def integrate_with_hitl_workflow() -> None:
    """Integrate notification service with HITL workflow manager and session preferences."""
    from packages.core.hitl.workflow import get_hitl_workflow_manager, Notification as HITLNotification
    from packages.core.sessions import get_session_manager

    workflow_mgr = get_hitl_workflow_manager()
    notification_svc = get_notification_service()
    session_mgr = get_session_manager()

    # Set up preferences lookup from session manager
    def preferences_lookup(user_id: str) -> dict:
        """Look up user notification preferences from session manager."""
        try:
            prefs = session_mgr.get_user_preferences(user_id)
            notif = prefs.notifications
            return {
                "escalation_alerts": {
                    "email": notif.escalation_alerts.email,
                    "push": notif.escalation_alerts.push,
                    "in_app": notif.escalation_alerts.in_app,
                },
                "draft_pending": {
                    "email": notif.draft_pending.email,
                    "push": notif.draft_pending.push,
                    "in_app": notif.draft_pending.in_app,
                },
                "policy_changes": {
                    "email": notif.policy_changes.email,
                    "push": notif.policy_changes.push,
                    "in_app": notif.policy_changes.in_app,
                },
                "sla_warnings": {
                    "email": notif.sla_warnings.email,
                    "push": notif.sla_warnings.push,
                    "in_app": notif.sla_warnings.in_app,
                },
                "weekly_summary": {
                    "email": notif.weekly_summary.email,
                    "push": notif.weekly_summary.push,
                    "in_app": notif.weekly_summary.in_app,
                },
                "enabled": notif.enabled,
            }
        except Exception as e:
            logger.warning(f"Failed to get preferences for {user_id}: {e}")
            return {}

    notification_svc.set_preferences_lookup(preferences_lookup)
    logger.info("Notification service connected to session preferences")

    async def hitl_notification_handler(notification: HITLNotification) -> None:
        """Handle HITL notifications and dispatch via notification service."""
        # Map HITL notification types to notification service types
        type_mapping = {
            "ESCALATION": "escalation_alerts",
            "ASSIGNMENT": "draft_pending",
            "SLA_WARNING": "sla_warnings",
            "APPROVED": "draft_pending",
            "REJECTED": "draft_pending",
        }

        notification_type = type_mapping.get(notification.type.value, "draft_pending")

        await notification_svc.send(
            notification_type=notification_type,
            recipient_id=notification.recipient_id,
            title=notification.title,
            message=notification.message,
            priority=NotificationPriority.HIGH if notification.type.value in ("ESCALATION", "SLA_WARNING") else NotificationPriority.NORMAL,
            metadata={
                "hitl_notification_id": notification.id,
                "approval_id": notification.approval_id,
                **(notification.metadata or {}),
            },
        )

    # Register as sync wrapper (workflow uses sync handlers)
    def sync_handler(notification: HITLNotification) -> None:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(hitl_notification_handler(notification))
            else:
                loop.run_until_complete(hitl_notification_handler(notification))
        except RuntimeError:
            # No event loop, create new one
            asyncio.run(hitl_notification_handler(notification))

    workflow_mgr.register_notification_handler(sync_handler)
    logger.info("Notification service integrated with HITL workflow")


__all__ = [
    "NotificationChannel",
    "NotificationPriority",
    "NotificationPayload",
    "NotificationAdapter",
    "EmailAdapter",
    "PushAdapter",
    "InAppAdapter",
    "NotificationService",
    "get_notification_service",
    "integrate_with_hitl_workflow",
]

"""Enhanced audit logging with compliance features."""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class AuditEventType(str, Enum):
    """Types of audit events."""

    QUERY = "QUERY"
    RESPONSE = "RESPONSE"
    AGENT_CREATE = "AGENT_CREATE"
    AGENT_UPDATE = "AGENT_UPDATE"
    AGENT_DELETE = "AGENT_DELETE"
    KNOWLEDGE_UPLOAD = "KNOWLEDGE_UPLOAD"
    KNOWLEDGE_DELETE = "KNOWLEDGE_DELETE"
    APPROVAL_CREATE = "APPROVAL_CREATE"
    APPROVAL_RESOLVE = "APPROVAL_RESOLVE"
    GUARDRAIL_TRIGGER = "GUARDRAIL_TRIGGER"
    PII_DETECTED = "PII_DETECTED"
    ESCALATION = "ESCALATION"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    CONFIG_CHANGE = "CONFIG_CHANGE"
    EXPORT = "EXPORT"


class SeverityLevel(str, Enum):
    """Audit event severity levels."""

    INFO = "INFO"
    WARNING = "WARNING"
    ALERT = "ALERT"
    CRITICAL = "CRITICAL"


class PIIType(str, Enum):
    """Types of PII that can be detected."""

    SSN = "SSN"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    CREDIT_CARD = "CREDIT_CARD"
    ADDRESS = "ADDRESS"
    DOB = "DOB"
    NAME = "NAME"
    MEDICAL = "MEDICAL"


class AuditEvent(BaseModel):
    """A single audit event."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    event_type: AuditEventType
    severity: SeverityLevel = SeverityLevel.INFO

    # Actor information
    user_id: str = "system"
    user_department: str = "System"
    user_role: str = "system"
    ip_address: str | None = None
    user_agent: str | None = None

    # Context
    agent_id: str | None = None
    agent_name: str | None = None
    session_id: str | None = None
    request_id: str | None = None

    # Content (sanitized)
    action: str  # Brief description of action
    details: dict[str, Any] = Field(default_factory=dict)

    # Compliance
    pii_detected: list[str] = Field(default_factory=list)
    guardrails_triggered: list[str] = Field(default_factory=list)
    requires_review: bool = False
    reviewed_by: str | None = None
    reviewed_at: str | None = None


class AuditSummary(BaseModel):
    """Summary of audit events."""

    period_start: str
    period_end: str
    total_events: int = 0
    events_by_type: dict[str, int] = Field(default_factory=dict)
    events_by_severity: dict[str, int] = Field(default_factory=dict)
    events_by_user: dict[str, int] = Field(default_factory=dict)
    events_by_agent: dict[str, int] = Field(default_factory=dict)
    pii_detections: int = 0
    guardrail_triggers: int = 0
    escalations: int = 0
    pending_review: int = 0


class ComplianceReport(BaseModel):
    """FOIA-ready compliance report."""

    report_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    generated_by: str = "system"
    period_start: str
    period_end: str
    summary: AuditSummary
    events: list[AuditEvent] = Field(default_factory=list)
    filters_applied: dict[str, Any] = Field(default_factory=dict)


class AuditManager:
    """Manages audit logging and compliance."""

    def __init__(self, storage_path: str | None = None):
        if storage_path is None:
            storage_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", "data", "audit"
            )
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Events storage (organized by date)
        self._events_path = self.storage_path / "events"
        self._events_path.mkdir(exist_ok=True)

        # PII patterns for detection
        self._pii_patterns = {
            PIIType.SSN: r'\b\d{3}-\d{2}-\d{4}\b',
            PIIType.EMAIL: r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            PIIType.PHONE: r'\b(?:\+1)?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
            PIIType.CREDIT_CARD: r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
            PIIType.DOB: r'\b(?:0[1-9]|1[0-2])/(?:0[1-9]|[12]\d|3[01])/(?:19|20)\d{2}\b',
        }

    def _get_daily_file(self, date: str) -> Path:
        """Get the audit file for a specific date."""
        return self._events_path / f"audit_{date}.json"

    def _load_daily_events(self, date: str) -> list[AuditEvent]:
        """Load events for a specific date."""
        file_path = self._get_daily_file(date)
        if file_path.exists():
            try:
                with open(file_path) as f:
                    data = json.load(f)
                    return [AuditEvent(**e) for e in data]
            except Exception:
                return []
        return []

    def _save_daily_events(self, date: str, events: list[AuditEvent]) -> None:
        """Save events for a specific date."""
        file_path = self._get_daily_file(date)
        data = [e.model_dump() for e in events]
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

    # =========================================================================
    # PII Detection
    # =========================================================================

    def detect_pii(self, text: str) -> list[str]:
        """Detect PII in text."""
        detected = []
        for pii_type, pattern in self._pii_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                detected.append(pii_type.value)
        return detected

    def sanitize_text(self, text: str) -> str:
        """Sanitize PII from text for logging."""
        result = text
        for pii_type, pattern in self._pii_patterns.items():
            result = re.sub(pattern, f"[{pii_type.value}_REDACTED]", result, flags=re.IGNORECASE)
        return result

    # =========================================================================
    # Event Logging
    # =========================================================================

    def log_event(
        self,
        event_type: AuditEventType,
        action: str,
        user_id: str = "system",
        user_department: str = "System",
        user_role: str = "system",
        agent_id: str | None = None,
        agent_name: str | None = None,
        session_id: str | None = None,
        details: dict[str, Any] | None = None,
        severity: SeverityLevel = SeverityLevel.INFO,
        ip_address: str | None = None,
        check_pii: bool = True,
    ) -> AuditEvent:
        """Log an audit event."""
        # Check for PII in action and details
        pii_detected = []
        if check_pii:
            pii_detected.extend(self.detect_pii(action))
            if details:
                for value in details.values():
                    if isinstance(value, str):
                        pii_detected.extend(self.detect_pii(value))

        # Determine if review is needed
        requires_review = bool(pii_detected) or severity in {SeverityLevel.ALERT, SeverityLevel.CRITICAL}

        event = AuditEvent(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            user_department=user_department,
            user_role=user_role,
            ip_address=ip_address,
            agent_id=agent_id,
            agent_name=agent_name,
            session_id=session_id,
            action=action,
            details=details or {},
            pii_detected=list(set(pii_detected)),
            requires_review=requires_review,
        )

        # Save to daily file
        date = event.timestamp[:10]
        events = self._load_daily_events(date)
        events.append(event)
        self._save_daily_events(date, events)

        return event

    def log_query(
        self,
        user_id: str,
        agent_id: str,
        agent_name: str,
        query: str,
        response: str,
        user_department: str = "General",
        guardrails_triggered: list[str] | None = None,
        session_id: str | None = None,
        ip_address: str | None = None,
    ) -> AuditEvent:
        """Log a query event with full context."""
        # Check for PII
        pii_in_query = self.detect_pii(query)
        pii_in_response = self.detect_pii(response)

        severity = SeverityLevel.INFO
        if pii_in_query or pii_in_response:
            severity = SeverityLevel.WARNING
        if guardrails_triggered:
            severity = SeverityLevel.ALERT

        return self.log_event(
            event_type=AuditEventType.QUERY,
            action=f"Query to {agent_name}",
            user_id=user_id,
            user_department=user_department,
            agent_id=agent_id,
            agent_name=agent_name,
            session_id=session_id,
            ip_address=ip_address,
            severity=severity,
            details={
                "query_preview": self.sanitize_text(query[:200]),
                "response_preview": self.sanitize_text(response[:200]),
                "query_length": len(query),
                "response_length": len(response),
                "pii_in_query": pii_in_query,
                "pii_in_response": pii_in_response,
                "guardrails_triggered": guardrails_triggered or [],
            },
            check_pii=False,  # Already checked
        )

    def log_guardrail_trigger(
        self,
        user_id: str,
        agent_id: str,
        agent_name: str,
        guardrail: str,
        context: str,
    ) -> AuditEvent:
        """Log a guardrail trigger event."""
        return self.log_event(
            event_type=AuditEventType.GUARDRAIL_TRIGGER,
            action=f"Guardrail triggered: {guardrail}",
            user_id=user_id,
            agent_id=agent_id,
            agent_name=agent_name,
            severity=SeverityLevel.ALERT,
            details={
                "guardrail": guardrail,
                "context_preview": self.sanitize_text(context[:200]),
            },
        )

    # =========================================================================
    # Query and Reporting
    # =========================================================================

    def get_events(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        event_type: AuditEventType | None = None,
        user_id: str | None = None,
        agent_id: str | None = None,
        severity: SeverityLevel | None = None,
        requires_review: bool | None = None,
        limit: int = 1000,
    ) -> list[AuditEvent]:
        """Get audit events with filtering."""
        if not start_date:
            start_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.utcnow().strftime("%Y-%m-%d")

        all_events = []

        # Load events from date range
        current = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            events = self._load_daily_events(date_str)
            all_events.extend(events)
            current += timedelta(days=1)

        # Apply filters
        if event_type:
            all_events = [e for e in all_events if e.event_type == event_type]
        if user_id:
            all_events = [e for e in all_events if e.user_id == user_id]
        if agent_id:
            all_events = [e for e in all_events if e.agent_id == agent_id]
        if severity:
            all_events = [e for e in all_events if e.severity == severity]
        if requires_review is not None:
            all_events = [e for e in all_events if e.requires_review == requires_review]

        # Sort by timestamp descending
        all_events.sort(key=lambda e: e.timestamp, reverse=True)

        return all_events[:limit]

    def get_summary(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> AuditSummary:
        """Get audit summary for a period."""
        if not start_date:
            start_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.utcnow().strftime("%Y-%m-%d")

        events = self.get_events(start_date=start_date, end_date=end_date, limit=100000)

        summary = AuditSummary(
            period_start=start_date,
            period_end=end_date,
            total_events=len(events),
        )

        for event in events:
            # By type
            event_type = event.event_type.value
            summary.events_by_type[event_type] = summary.events_by_type.get(event_type, 0) + 1

            # By severity
            sev = event.severity.value
            summary.events_by_severity[sev] = summary.events_by_severity.get(sev, 0) + 1

            # By user
            summary.events_by_user[event.user_id] = summary.events_by_user.get(event.user_id, 0) + 1

            # By agent
            if event.agent_id:
                summary.events_by_agent[event.agent_id] = summary.events_by_agent.get(event.agent_id, 0) + 1

            # Counts
            if event.pii_detected:
                summary.pii_detections += 1
            if event.guardrails_triggered:
                summary.guardrail_triggers += 1
            if event.event_type == AuditEventType.ESCALATION:
                summary.escalations += 1
            if event.requires_review and not event.reviewed_by:
                summary.pending_review += 1

        return summary

    def generate_compliance_report(
        self,
        start_date: str,
        end_date: str,
        generated_by: str = "system",
        filters: dict[str, Any] | None = None,
    ) -> ComplianceReport:
        """Generate a FOIA-ready compliance report."""
        events = self.get_events(
            start_date=start_date,
            end_date=end_date,
            limit=100000,
        )

        summary = self.get_summary(start_date=start_date, end_date=end_date)

        return ComplianceReport(
            generated_by=generated_by,
            period_start=start_date,
            period_end=end_date,
            summary=summary,
            events=events,
            filters_applied=filters or {},
        )

    def mark_reviewed(
        self,
        event_id: str,
        reviewer_id: str,
    ) -> bool:
        """Mark an event as reviewed."""
        # Search through recent files
        for i in range(30):
            date = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
            events = self._load_daily_events(date)
            for event in events:
                if event.id == event_id:
                    event.reviewed_by = reviewer_id
                    event.reviewed_at = datetime.utcnow().isoformat()
                    self._save_daily_events(date, events)
                    return True
        return False


# Singleton instance
_audit_manager: AuditManager | None = None


def get_audit_manager() -> AuditManager:
    """Get the audit manager singleton."""
    global _audit_manager
    if _audit_manager is None:
        _audit_manager = AuditManager()
    return _audit_manager


__all__ = [
    "AuditEventType",
    "SeverityLevel",
    "PIIType",
    "AuditEvent",
    "AuditSummary",
    "ComplianceReport",
    "AuditManager",
    "get_audit_manager",
]

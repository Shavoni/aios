"""Voice Audit Logging - Universal logging across all providers.

Regardless of which provider is used (Deepgram, Whisper, ElevenLabs, etc.),
all voice events are logged in a consistent format for compliance and debugging.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, UTC
from enum import Enum
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field


class VoiceEventType(str, Enum):
    """Types of voice events to audit."""

    # Session lifecycle
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    SESSION_TIMEOUT = "session_timeout"

    # STT events
    STT_START = "stt_start"
    STT_INTERIM = "stt_interim"
    STT_FINAL = "stt_final"
    STT_ERROR = "stt_error"

    # TTS events
    TTS_START = "tts_start"
    TTS_CHUNK = "tts_chunk"
    TTS_COMPLETE = "tts_complete"
    TTS_ERROR = "tts_error"

    # Interaction events
    BARGE_IN = "barge_in"
    USER_INTERRUPT = "user_interrupt"

    # Routing events
    PROVIDER_SELECTED = "provider_selected"
    PROVIDER_FALLBACK = "provider_fallback"
    PROVIDER_CIRCUIT_OPEN = "provider_circuit_open"
    PROVIDER_CIRCUIT_CLOSE = "provider_circuit_close"

    # Tool/action events
    TOOL_TRIGGERED = "tool_triggered"
    TOOL_APPROVED = "tool_approved"
    TOOL_REJECTED = "tool_rejected"

    # Compliance events
    PII_DETECTED = "pii_detected"
    PII_REDACTED = "pii_redacted"
    ESCALATION = "escalation"


class VoiceAuditEvent(BaseModel):
    """A single voice audit event."""

    # Identification
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: VoiceEventType
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    # Context
    session_id: str
    org_id: str
    department_id: str = ""
    user_id: str = ""

    # Provider info
    provider_id: str = ""
    provider_name: str = ""
    profile_id: str = ""

    # Performance
    latency_ms: float = 0.0
    duration_ms: float = 0.0

    # Content (may be redacted)
    transcript: str | None = None  # STT result
    tts_text: str | None = None  # TTS input
    is_redacted: bool = False

    # Routing
    fallback_count: int = 0
    fallback_reason: str = ""

    # Tool calls
    tool_name: str | None = None
    tool_approved: bool | None = None
    approval_reason: str = ""

    # Governance
    policy_version: int = 0
    policy_hash: str = ""
    governance_triggered: list[str] = Field(default_factory=list)

    # Error info
    error_code: str = ""
    error_message: str = ""

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)


class VoiceAuditLog:
    """Manages voice audit logging."""

    def __init__(self, storage_path: str | None = None):
        if storage_path is None:
            storage_path = str(Path(__file__).parent.parent.parent.parent / "data" / "voice_audit")
        self._storage_path = Path(storage_path)
        self._storage_path.mkdir(parents=True, exist_ok=True)

        self._events: list[VoiceAuditEvent] = []
        self._callbacks: list[callable] = []

    def log(self, event: VoiceAuditEvent) -> None:
        """Log a voice audit event."""
        self._events.append(event)

        # Persist to file (append mode for performance)
        log_file = self._storage_path / f"voice_audit_{datetime.now(UTC).strftime('%Y%m%d')}.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(event.model_dump_json() + "\n")

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception:
                pass

    def log_session_start(
        self,
        session_id: str,
        org_id: str,
        profile_id: str,
        provider_id: str,
        provider_name: str,
        department_id: str = "",
        user_id: str = "",
        policy_version: int = 0,
        policy_hash: str = "",
    ) -> VoiceAuditEvent:
        """Log a session start event."""
        event = VoiceAuditEvent(
            event_type=VoiceEventType.SESSION_START,
            session_id=session_id,
            org_id=org_id,
            department_id=department_id,
            user_id=user_id,
            provider_id=provider_id,
            provider_name=provider_name,
            profile_id=profile_id,
            policy_version=policy_version,
            policy_hash=policy_hash,
        )
        self.log(event)
        return event

    def log_session_end(
        self,
        session_id: str,
        org_id: str,
        duration_ms: float,
        fallback_count: int = 0,
    ) -> VoiceAuditEvent:
        """Log a session end event."""
        event = VoiceAuditEvent(
            event_type=VoiceEventType.SESSION_END,
            session_id=session_id,
            org_id=org_id,
            duration_ms=duration_ms,
            fallback_count=fallback_count,
        )
        self.log(event)
        return event

    def log_stt(
        self,
        session_id: str,
        org_id: str,
        provider_id: str,
        transcript: str,
        is_final: bool = True,
        latency_ms: float = 0.0,
        is_redacted: bool = False,
        department_id: str = "",
        user_id: str = "",
    ) -> VoiceAuditEvent:
        """Log an STT (speech-to-text) event."""
        event = VoiceAuditEvent(
            event_type=VoiceEventType.STT_FINAL if is_final else VoiceEventType.STT_INTERIM,
            session_id=session_id,
            org_id=org_id,
            department_id=department_id,
            user_id=user_id,
            provider_id=provider_id,
            transcript=transcript,
            is_redacted=is_redacted,
            latency_ms=latency_ms,
        )
        self.log(event)
        return event

    def log_tts(
        self,
        session_id: str,
        org_id: str,
        provider_id: str,
        text: str,
        is_complete: bool = True,
        latency_ms: float = 0.0,
        duration_ms: float = 0.0,
        department_id: str = "",
        user_id: str = "",
    ) -> VoiceAuditEvent:
        """Log a TTS (text-to-speech) event."""
        event = VoiceAuditEvent(
            event_type=VoiceEventType.TTS_COMPLETE if is_complete else VoiceEventType.TTS_START,
            session_id=session_id,
            org_id=org_id,
            department_id=department_id,
            user_id=user_id,
            provider_id=provider_id,
            tts_text=text,
            latency_ms=latency_ms,
            duration_ms=duration_ms,
        )
        self.log(event)
        return event

    def log_provider_selected(
        self,
        session_id: str,
        org_id: str,
        provider_id: str,
        provider_name: str,
        profile_id: str,
        reason: str = "",
    ) -> VoiceAuditEvent:
        """Log provider selection."""
        event = VoiceAuditEvent(
            event_type=VoiceEventType.PROVIDER_SELECTED,
            session_id=session_id,
            org_id=org_id,
            provider_id=provider_id,
            provider_name=provider_name,
            profile_id=profile_id,
            metadata={"selection_reason": reason},
        )
        self.log(event)
        return event

    def log_fallback(
        self,
        session_id: str,
        org_id: str,
        old_provider_id: str,
        new_provider_id: str,
        new_provider_name: str,
        reason: str,
        fallback_count: int,
    ) -> VoiceAuditEvent:
        """Log a provider fallback event."""
        event = VoiceAuditEvent(
            event_type=VoiceEventType.PROVIDER_FALLBACK,
            session_id=session_id,
            org_id=org_id,
            provider_id=new_provider_id,
            provider_name=new_provider_name,
            fallback_count=fallback_count,
            fallback_reason=reason,
            metadata={"old_provider_id": old_provider_id},
        )
        self.log(event)
        return event

    def log_tool_call(
        self,
        session_id: str,
        org_id: str,
        tool_name: str,
        approved: bool,
        reason: str = "",
        department_id: str = "",
        user_id: str = "",
    ) -> VoiceAuditEvent:
        """Log a tool/action trigger and approval status."""
        event = VoiceAuditEvent(
            event_type=VoiceEventType.TOOL_APPROVED if approved else VoiceEventType.TOOL_REJECTED,
            session_id=session_id,
            org_id=org_id,
            department_id=department_id,
            user_id=user_id,
            tool_name=tool_name,
            tool_approved=approved,
            approval_reason=reason,
        )
        self.log(event)
        return event

    def log_pii_event(
        self,
        session_id: str,
        org_id: str,
        detected: bool,
        redacted: bool,
        pii_types: list[str] | None = None,
    ) -> VoiceAuditEvent:
        """Log PII detection/redaction."""
        event = VoiceAuditEvent(
            event_type=VoiceEventType.PII_REDACTED if redacted else VoiceEventType.PII_DETECTED,
            session_id=session_id,
            org_id=org_id,
            is_redacted=redacted,
            metadata={"pii_types": pii_types or []},
        )
        self.log(event)
        return event

    def log_error(
        self,
        session_id: str,
        org_id: str,
        event_type: VoiceEventType,
        error_code: str,
        error_message: str,
        provider_id: str = "",
    ) -> VoiceAuditEvent:
        """Log an error event."""
        event = VoiceAuditEvent(
            event_type=event_type,
            session_id=session_id,
            org_id=org_id,
            provider_id=provider_id,
            error_code=error_code,
            error_message=error_message,
        )
        self.log(event)
        return event

    def on_event(self, callback: callable) -> None:
        """Register a callback for all audit events."""
        self._callbacks.append(callback)

    # -------------------------------------------------------------------------
    # Query Methods
    # -------------------------------------------------------------------------

    def get_session_events(self, session_id: str) -> list[VoiceAuditEvent]:
        """Get all events for a session."""
        return [e for e in self._events if e.session_id == session_id]

    def get_events_by_type(
        self,
        event_type: VoiceEventType,
        limit: int = 100,
    ) -> list[VoiceAuditEvent]:
        """Get events by type."""
        matching = [e for e in self._events if e.event_type == event_type]
        return matching[-limit:]

    def get_events_by_org(
        self,
        org_id: str,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int = 1000,
    ) -> list[VoiceAuditEvent]:
        """Get events for an organization within a time range."""
        matching = [e for e in self._events if e.org_id == org_id]

        if start_time:
            matching = [e for e in matching if e.timestamp >= start_time]
        if end_time:
            matching = [e for e in matching if e.timestamp <= end_time]

        return matching[-limit:]

    def get_summary(self, org_id: str | None = None) -> dict[str, Any]:
        """Get audit summary statistics."""
        events = self._events
        if org_id:
            events = [e for e in events if e.org_id == org_id]

        if not events:
            return {
                "total_events": 0,
                "events_by_type": {},
                "providers_used": [],
                "avg_latency_ms": 0,
                "fallback_count": 0,
                "error_count": 0,
            }

        # Count by type
        by_type: dict[str, int] = {}
        for e in events:
            by_type[e.event_type.value] = by_type.get(e.event_type.value, 0) + 1

        # Unique providers
        providers = list(set(e.provider_id for e in events if e.provider_id))

        # Average latency (for events with latency)
        latencies = [e.latency_ms for e in events if e.latency_ms > 0]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0

        # Fallback count
        fallback_count = sum(1 for e in events if e.event_type == VoiceEventType.PROVIDER_FALLBACK)

        # Error count
        error_types = {VoiceEventType.STT_ERROR, VoiceEventType.TTS_ERROR}
        error_count = sum(1 for e in events if e.event_type in error_types)

        return {
            "total_events": len(events),
            "events_by_type": by_type,
            "providers_used": providers,
            "avg_latency_ms": round(avg_latency, 2),
            "fallback_count": fallback_count,
            "error_count": error_count,
        }

    def export_session(self, session_id: str) -> str:
        """Export session events as JSONL."""
        events = self.get_session_events(session_id)
        lines = [e.model_dump_json() for e in events]
        return "\n".join(lines)


# Singleton instance
_audit_log: VoiceAuditLog | None = None


def get_voice_audit_log() -> VoiceAuditLog:
    """Get the voice audit log singleton."""
    global _audit_log
    if _audit_log is None:
        _audit_log = VoiceAuditLog()
    return _audit_log


__all__ = [
    "VoiceEventType",
    "VoiceAuditEvent",
    "VoiceAuditLog",
    "get_voice_audit_log",
]

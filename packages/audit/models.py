"""Audit data models.

Immutable audit records with hash chaining for tamper-evident logging.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AuditEventType(str, Enum):
    """Types of auditable events."""

    # Query events
    AGENT_QUERY = "agent_query"
    AGENT_RESPONSE = "agent_response"

    # Authentication events
    AUTH_LOGIN = "auth_login"
    AUTH_LOGOUT = "auth_logout"
    AUTH_FAILED = "auth_failed"
    AUTH_TOKEN_REFRESH = "auth_token_refresh"

    # Authorization events
    AUTHZ_GRANTED = "authz_granted"
    AUTHZ_DENIED = "authz_denied"

    # Data access events
    DATA_READ = "data_read"
    DATA_CREATE = "data_create"
    DATA_UPDATE = "data_update"
    DATA_DELETE = "data_delete"

    # Governance events
    GOVERNANCE_TRIGGERED = "governance_triggered"
    GOVERNANCE_OVERRIDE = "governance_override"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"

    # Configuration events
    CONFIG_CHANGE = "config_change"
    POLICY_CHANGE = "policy_change"
    AGENT_DEPLOYED = "agent_deployed"
    AGENT_RETIRED = "agent_retired"

    # Knowledge base events
    KB_DOCUMENT_ADDED = "kb_document_added"
    KB_DOCUMENT_REMOVED = "kb_document_removed"
    KB_SYNC_COMPLETED = "kb_sync_completed"

    # Security events
    SECURITY_ALERT = "security_alert"
    ANOMALY_DETECTED = "anomaly_detected"

    # System events
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"
    SYSTEM_ERROR = "system_error"


class AuditSeverity(str, Enum):
    """Severity levels for audit events."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ActorType(str, Enum):
    """Types of actors that can perform actions."""

    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"
    SERVICE = "service"
    EXTERNAL = "external"


class ImmutableAuditRecord(BaseModel):
    """Tamper-evident audit record with hash chaining.

    This record is designed to be immutable once created.
    The hash chain ensures any modification can be detected.

    Chain integrity:
    - Each record's `record_hash` is computed from its contents + `previous_hash`
    - `previous_hash` links to the prior record in the chain
    - Genesis record has empty `previous_hash`
    - Chain verification walks all records and validates hashes
    """

    # Identity
    record_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this record"
    )
    sequence_number: int = Field(
        description="Monotonically increasing sequence within tenant"
    )
    tenant_id: str = Field(description="Tenant this record belongs to")

    # Timing
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this event occurred"
    )

    # Event details
    event_type: AuditEventType = Field(description="Type of auditable event")
    severity: AuditSeverity = Field(
        default=AuditSeverity.INFO,
        description="Event severity"
    )

    # Actor information
    actor_id: str = Field(description="Who performed the action")
    actor_type: ActorType = Field(
        default=ActorType.USER,
        description="Type of actor"
    )
    actor_ip: str | None = Field(
        default=None,
        description="IP address of actor"
    )

    # Action details
    action: str = Field(description="Human-readable action description")
    resource_type: str | None = Field(
        default=None,
        description="Type of resource affected"
    )
    resource_id: str | None = Field(
        default=None,
        description="ID of resource affected"
    )

    # Outcome
    outcome: str = Field(
        default="success",
        description="Outcome: 'success', 'failure', 'partial'"
    )
    outcome_details: str | None = Field(
        default=None,
        description="Additional outcome details"
    )

    # Payload (structured event data)
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Event-specific structured data"
    )

    # Chain integrity
    previous_hash: str = Field(
        default="",
        description="Hash of previous record (empty for genesis)"
    )
    record_hash: str = Field(
        default="",
        description="Computed hash of this record"
    )

    # Metadata
    environment: str = Field(
        default="production",
        description="Environment: production, staging, development"
    )
    api_version: str = Field(
        default="1.0",
        description="API version that created this record"
    )
    correlation_id: str | None = Field(
        default=None,
        description="Request correlation ID for tracing"
    )

    class Config:
        """Pydantic configuration."""

        # Prevent modification after creation
        frozen = False  # We need to set record_hash after creation

    def to_hash_content(self) -> dict[str, Any]:
        """Get the content used for hash computation.

        Returns a deterministic dictionary of fields to hash.
        Excludes `record_hash` as that's what we're computing.
        """
        return {
            "record_id": self.record_id,
            "sequence_number": self.sequence_number,
            "tenant_id": self.tenant_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "actor_id": self.actor_id,
            "actor_type": self.actor_type.value,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "outcome": self.outcome,
            "payload": self.payload,
            "previous_hash": self.previous_hash,
            "environment": self.environment,
            "api_version": self.api_version,
        }


class AuditChainStatus(BaseModel):
    """Status of an audit chain."""

    tenant_id: str
    total_records: int
    first_record_id: str | None
    last_record_id: str | None
    last_sequence: int
    last_timestamp: datetime | None
    chain_valid: bool
    last_verified_at: datetime | None
    error_message: str | None = None


class AuditQuery(BaseModel):
    """Query parameters for audit log search."""

    tenant_id: str
    event_types: list[AuditEventType] | None = None
    actor_id: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    severity_min: AuditSeverity | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    limit: int = 100
    offset: int = 0

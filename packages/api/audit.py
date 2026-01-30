"""Audit API endpoints.

Provides access to immutable audit logs with chain verification.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from packages.audit.models import (
    AuditEventType,
    AuditSeverity,
    AuditChainStatus,
    ImmutableAuditRecord,
)
from packages.audit.chain import AuditChain
from packages.audit.storage import get_audit_storage

router = APIRouter(prefix="/audit", tags=["Audit"])

# Initialize audit system
_audit_storage = None
_audit_chain = None


def get_audit_chain() -> AuditChain:
    """Get or create the audit chain singleton."""
    global _audit_storage, _audit_chain
    if _audit_chain is None:
        _audit_storage = get_audit_storage()
        _audit_chain = AuditChain(_audit_storage)
    return _audit_chain


# =============================================================================
# Request/Response Models
# =============================================================================


class AuditQueryRequest(BaseModel):
    """Request to query audit logs."""

    tenant_id: str = Field(description="Tenant ID to query")
    event_types: list[str] | None = Field(
        default=None,
        description="Filter by event types"
    )
    actor_id: str | None = Field(default=None, description="Filter by actor")
    resource_type: str | None = Field(default=None, description="Filter by resource type")
    resource_id: str | None = Field(default=None, description="Filter by resource ID")
    start_time: datetime | None = Field(default=None, description="Start time filter")
    end_time: datetime | None = Field(default=None, description="End time filter")
    limit: int = Field(default=100, ge=1, le=1000, description="Max records to return")
    offset: int = Field(default=0, ge=0, description="Offset for pagination")


class AuditRecordResponse(BaseModel):
    """Audit record response."""

    record_id: str
    sequence_number: int
    tenant_id: str
    timestamp: datetime
    event_type: str
    severity: str
    actor_id: str
    actor_type: str
    action: str
    resource_type: str | None
    resource_id: str | None
    outcome: str
    payload: dict[str, Any]
    record_hash: str


class AuditQueryResponse(BaseModel):
    """Response containing audit records."""

    records: list[AuditRecordResponse]
    total: int
    has_more: bool


class ChainVerificationResponse(BaseModel):
    """Response from chain verification."""

    tenant_id: str
    is_valid: bool
    records_checked: int
    error_message: str | None = None
    verified_at: datetime


class RecordEventRequest(BaseModel):
    """Request to record an audit event."""

    tenant_id: str = Field(description="Tenant ID")
    event_type: str = Field(description="Event type (e.g., 'agent_query')")
    actor_id: str = Field(description="Actor performing the action")
    action: str = Field(description="Human-readable action description")
    actor_type: str = Field(default="user", description="Type of actor")
    severity: str = Field(default="info", description="Event severity")
    resource_type: str | None = Field(default=None, description="Type of resource affected")
    resource_id: str | None = Field(default=None, description="ID of resource affected")
    outcome: str = Field(default="success", description="Action outcome")
    payload: dict[str, Any] = Field(default_factory=dict, description="Event payload")
    correlation_id: str | None = Field(default=None, description="Correlation ID for tracing")


# =============================================================================
# Audit Endpoints
# =============================================================================


@router.get("/status/{tenant_id}", response_model=AuditChainStatus)
async def get_chain_status(tenant_id: str) -> AuditChainStatus:
    """Get the status of a tenant's audit chain."""
    chain = get_audit_chain()
    return await chain.get_chain_status(tenant_id)


@router.post("/verify/{tenant_id}", response_model=ChainVerificationResponse)
async def verify_chain(
    tenant_id: str,
    start_sequence: int = Query(default=1, ge=1, description="Start sequence"),
    end_sequence: int | None = Query(default=None, description="End sequence (None = latest)"),
) -> ChainVerificationResponse:
    """Verify the integrity of a tenant's audit chain.

    This performs cryptographic verification that the chain has not been tampered with.
    """
    chain = get_audit_chain()

    is_valid, error = await chain.verify_chain(
        tenant_id,
        start_sequence=start_sequence,
        end_sequence=end_sequence,
    )

    # Get count for response
    storage = chain.storage
    if end_sequence:
        records = await storage.get_range(tenant_id, start_sequence, end_sequence)
        records_checked = len(records)
    else:
        records_checked = await storage.count(tenant_id)

    return ChainVerificationResponse(
        tenant_id=tenant_id,
        is_valid=is_valid,
        records_checked=records_checked,
        error_message=error,
        verified_at=datetime.utcnow(),
    )


@router.post("/query", response_model=AuditQueryResponse)
async def query_audit_logs(request: AuditQueryRequest) -> AuditQueryResponse:
    """Query audit logs with filters."""
    chain = get_audit_chain()
    storage = chain.storage

    # Build query
    from packages.audit.models import AuditQuery

    event_types = None
    if request.event_types:
        event_types = [AuditEventType(et) for et in request.event_types]

    query = AuditQuery(
        tenant_id=request.tenant_id,
        event_types=event_types,
        actor_id=request.actor_id,
        resource_type=request.resource_type,
        resource_id=request.resource_id,
        start_time=request.start_time,
        end_time=request.end_time,
        limit=request.limit + 1,  # Fetch one extra to check has_more
        offset=request.offset,
    )

    records = await storage.query(query)

    # Check if there are more records
    has_more = len(records) > request.limit
    if has_more:
        records = records[:-1]  # Remove the extra record

    # Convert to response format
    response_records = [
        AuditRecordResponse(
            record_id=r.record_id,
            sequence_number=r.sequence_number,
            tenant_id=r.tenant_id,
            timestamp=r.timestamp,
            event_type=r.event_type.value if isinstance(r.event_type, AuditEventType) else r.event_type,
            severity=r.severity.value if isinstance(r.severity, AuditSeverity) else r.severity,
            actor_id=r.actor_id,
            actor_type=r.actor_type.value if hasattr(r.actor_type, 'value') else r.actor_type,
            action=r.action,
            resource_type=r.resource_type,
            resource_id=r.resource_id,
            outcome=r.outcome,
            payload=r.payload,
            record_hash=r.record_hash,
        )
        for r in records
    ]

    return AuditQueryResponse(
        records=response_records,
        total=len(response_records),
        has_more=has_more,
    )


@router.get("/{tenant_id}/recent", response_model=AuditQueryResponse)
async def get_recent_events(
    tenant_id: str,
    limit: int = Query(default=50, ge=1, le=500, description="Max records"),
) -> AuditQueryResponse:
    """Get recent audit events for a tenant."""
    chain = get_audit_chain()
    storage = chain.storage

    records = await storage.get_all(tenant_id, limit=limit)
    records = sorted(records, key=lambda r: r.timestamp, reverse=True)

    response_records = [
        AuditRecordResponse(
            record_id=r.record_id,
            sequence_number=r.sequence_number,
            tenant_id=r.tenant_id,
            timestamp=r.timestamp,
            event_type=r.event_type.value if isinstance(r.event_type, AuditEventType) else r.event_type,
            severity=r.severity.value if isinstance(r.severity, AuditSeverity) else r.severity,
            actor_id=r.actor_id,
            actor_type=r.actor_type.value if hasattr(r.actor_type, 'value') else r.actor_type,
            action=r.action,
            resource_type=r.resource_type,
            resource_id=r.resource_id,
            outcome=r.outcome,
            payload=r.payload,
            record_hash=r.record_hash,
        )
        for r in records
    ]

    return AuditQueryResponse(
        records=response_records,
        total=len(response_records),
        has_more=False,
    )


@router.post("/record", response_model=AuditRecordResponse, status_code=status.HTTP_201_CREATED)
async def record_event(request: RecordEventRequest) -> AuditRecordResponse:
    """Record an audit event.

    Note: Most events are recorded automatically by the system.
    This endpoint is for explicit event recording when needed.
    """
    chain = get_audit_chain()

    try:
        event_type = AuditEventType(request.event_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid event_type: {request.event_type}. Valid types: {[e.value for e in AuditEventType]}",
        )

    try:
        severity = AuditSeverity(request.severity)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid severity: {request.severity}. Valid values: {[s.value for s in AuditSeverity]}",
        )

    record = await chain.append_record(
        tenant_id=request.tenant_id,
        event_type=event_type,
        actor_id=request.actor_id,
        action=request.action,
        payload=request.payload,
        severity=severity,
        resource_type=request.resource_type,
        resource_id=request.resource_id,
        outcome=request.outcome,
        correlation_id=request.correlation_id,
    )

    return AuditRecordResponse(
        record_id=record.record_id,
        sequence_number=record.sequence_number,
        tenant_id=record.tenant_id,
        timestamp=record.timestamp,
        event_type=record.event_type.value,
        severity=record.severity.value,
        actor_id=record.actor_id,
        actor_type=record.actor_type.value,
        action=record.action,
        resource_type=record.resource_type,
        resource_id=record.resource_id,
        outcome=record.outcome,
        payload=record.payload,
        record_hash=record.record_hash,
    )


@router.get("/event-types", response_model=list[str])
async def list_event_types() -> list[str]:
    """List all available audit event types."""
    return [e.value for e in AuditEventType]

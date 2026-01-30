"""Audit hash chain implementation.

Provides tamper-evident audit logging through cryptographic hash chaining.
Each record links to its predecessor, forming an immutable chain.
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Protocol

from packages.audit.models import (
    ImmutableAuditRecord,
    AuditEventType,
    AuditSeverity,
    ActorType,
    AuditChainStatus,
)

logger = logging.getLogger(__name__)


class AuditStorage(Protocol):
    """Protocol for audit storage backends.

    Implementations must provide append-only semantics.
    Updates and deletes should be blocked at the storage level.
    """

    async def append(self, record: ImmutableAuditRecord) -> None:
        """Append a record (insert only, no updates)."""
        ...

    async def get_latest(self, tenant_id: str) -> ImmutableAuditRecord | None:
        """Get the most recent record for a tenant."""
        ...

    async def get_by_sequence(
        self, tenant_id: str, sequence: int
    ) -> ImmutableAuditRecord | None:
        """Get a record by sequence number."""
        ...

    async def get_range(
        self,
        tenant_id: str,
        start_sequence: int,
        end_sequence: int,
    ) -> list[ImmutableAuditRecord]:
        """Get records in a sequence range."""
        ...

    async def get_all(
        self, tenant_id: str, limit: int = 10000
    ) -> list[ImmutableAuditRecord]:
        """Get all records for a tenant (ordered by sequence)."""
        ...

    async def count(self, tenant_id: str) -> int:
        """Get total record count for a tenant."""
        ...


class AuditChain:
    """Manages hash-chained audit records.

    Ensures tamper-evident logging by:
    1. Computing cryptographic hash of each record
    2. Including previous record's hash in computation
    3. Storing records in append-only storage
    4. Providing chain verification

    Usage:
        chain = AuditChain(storage)

        # Record events
        await chain.append_record(
            tenant_id="tenant-123",
            event_type=AuditEventType.AGENT_QUERY,
            actor_id="user@example.com",
            action="Queried HR agent",
            payload={"query": "...", "agent_id": "..."}
        )

        # Verify integrity
        valid, error = await chain.verify_chain("tenant-123")
    """

    HASH_ALGORITHM = "sha256"

    def __init__(self, storage: AuditStorage):
        """Initialize audit chain with storage backend."""
        self.storage = storage

    def compute_record_hash(self, record: ImmutableAuditRecord) -> str:
        """Compute cryptographic hash for a record.

        Uses SHA-256 on canonical JSON representation.
        Includes previous_hash to form the chain.
        """
        # Get deterministic content
        content = record.to_hash_content()

        # Canonical JSON serialization (sorted keys, no whitespace)
        canonical = json.dumps(content, sort_keys=True, separators=(",", ":"))

        # Compute hash
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    async def append_record(
        self,
        tenant_id: str,
        event_type: AuditEventType,
        actor_id: str,
        action: str,
        payload: dict[str, Any] | None = None,
        actor_type: ActorType = ActorType.USER,
        severity: AuditSeverity = AuditSeverity.INFO,
        resource_type: str | None = None,
        resource_id: str | None = None,
        outcome: str = "success",
        correlation_id: str | None = None,
        actor_ip: str | None = None,
    ) -> ImmutableAuditRecord:
        """Create and append a new audit record.

        Automatically handles:
        - Sequence number assignment
        - Previous hash linking
        - Record hash computation
        - Append-only storage

        Returns:
            The created audit record
        """
        # Get previous record for chaining
        previous = await self.storage.get_latest(tenant_id)

        if previous:
            previous_hash = previous.record_hash
            sequence = previous.sequence_number + 1
        else:
            previous_hash = ""  # Genesis record
            sequence = 1

        # Create record
        record = ImmutableAuditRecord(
            sequence_number=sequence,
            tenant_id=tenant_id,
            event_type=event_type,
            severity=severity,
            actor_id=actor_id,
            actor_type=actor_type,
            actor_ip=actor_ip,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
            payload=payload or {},
            previous_hash=previous_hash,
            correlation_id=correlation_id,
        )

        # Compute hash
        record.record_hash = self.compute_record_hash(record)

        # Append to storage
        await self.storage.append(record)

        logger.debug(
            "Appended audit record: tenant=%s seq=%d type=%s hash=%s",
            tenant_id,
            sequence,
            event_type.value,
            record.record_hash[:16] + "...",
        )

        return record

    async def verify_chain(
        self, tenant_id: str, start_sequence: int = 1, end_sequence: int | None = None
    ) -> tuple[bool, str | None]:
        """Verify integrity of the audit chain.

        Walks the chain and validates:
        1. Each record's hash matches its content
        2. Each record's previous_hash matches the prior record
        3. Sequence numbers are continuous

        Args:
            tenant_id: Tenant whose chain to verify
            start_sequence: Starting sequence (default: 1)
            end_sequence: Ending sequence (default: latest)

        Returns:
            Tuple of (is_valid, error_message)
            - (True, None) if chain is valid
            - (False, "description") if tampering detected
        """
        # Get all records in range
        if end_sequence:
            records = await self.storage.get_range(
                tenant_id, start_sequence, end_sequence
            )
        else:
            records = await self.storage.get_all(tenant_id)

        if not records:
            return True, None  # Empty chain is valid

        # Sort by sequence (should already be sorted)
        records.sort(key=lambda r: r.sequence_number)

        # Verify first record
        first = records[0]
        if start_sequence == 1 and first.previous_hash != "":
            return False, f"Genesis record (seq=1) has non-empty previous_hash"

        # Verify hash of first record
        computed = self.compute_record_hash(first)
        if computed != first.record_hash:
            return False, (
                f"Hash mismatch at sequence {first.sequence_number}: "
                f"expected {first.record_hash[:16]}..., got {computed[:16]}..."
            )

        # Walk the chain
        previous_hash = first.record_hash
        previous_sequence = first.sequence_number

        for record in records[1:]:
            # Check sequence continuity
            if record.sequence_number != previous_sequence + 1:
                return False, (
                    f"Sequence gap: expected {previous_sequence + 1}, "
                    f"got {record.sequence_number}"
                )

            # Check previous hash link
            if record.previous_hash != previous_hash:
                return False, (
                    f"Chain break at sequence {record.sequence_number}: "
                    f"previous_hash mismatch"
                )

            # Verify record hash
            computed = self.compute_record_hash(record)
            if computed != record.record_hash:
                return False, (
                    f"Hash mismatch at sequence {record.sequence_number}: "
                    f"tampering detected"
                )

            # Move to next
            previous_hash = record.record_hash
            previous_sequence = record.sequence_number

        logger.info(
            "Chain verification passed: tenant=%s records=%d",
            tenant_id,
            len(records),
        )

        return True, None

    async def get_chain_status(self, tenant_id: str) -> AuditChainStatus:
        """Get current status of the audit chain."""
        count = await self.storage.count(tenant_id)
        latest = await self.storage.get_latest(tenant_id)

        # Quick verification (last 10 records)
        valid = True
        error = None
        if count > 0:
            start = max(1, (latest.sequence_number if latest else 1) - 10)
            valid, error = await self.verify_chain(tenant_id, start_sequence=start)

        return AuditChainStatus(
            tenant_id=tenant_id,
            total_records=count,
            first_record_id=None,  # Would need another query
            last_record_id=latest.record_id if latest else None,
            last_sequence=latest.sequence_number if latest else 0,
            last_timestamp=latest.timestamp if latest else None,
            chain_valid=valid,
            last_verified_at=datetime.utcnow(),
            error_message=error,
        )


# Convenience function for common audit events
async def audit_agent_query(
    chain: AuditChain,
    tenant_id: str,
    user_id: str,
    agent_id: str,
    query: str,
    response: str,
    grounding_score: float,
    sources_used: list[str],
    hitl_mode: str,
    correlation_id: str | None = None,
) -> ImmutableAuditRecord:
    """Record an agent query event with full context."""
    return await chain.append_record(
        tenant_id=tenant_id,
        event_type=AuditEventType.AGENT_QUERY,
        actor_id=user_id,
        action=f"Queried agent {agent_id}",
        resource_type="agent",
        resource_id=agent_id,
        payload={
            "query": query,
            "response": response,
            "grounding_score": grounding_score,
            "sources_used": sources_used,
            "hitl_mode": hitl_mode,
        },
        correlation_id=correlation_id,
    )

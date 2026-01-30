"""HAAIS AIOS Audit Package.

Tamper-evident audit logging with hash chaining for
enterprise compliance and accountability.

Features:
- Append-only audit records
- Cryptographic hash chaining
- Chain integrity verification
- WORM storage integration (optional)

Usage:
    from packages.audit import AuditChain, ImmutableAuditRecord

    chain = AuditChain(storage)

    # Record an event
    record = await chain.append_record(
        tenant_id="cleveland",
        event_type="agent_query",
        actor_id="user@example.com",
        payload={"query": "...", "response": "..."}
    )

    # Verify chain integrity
    valid, error = await chain.verify_chain("cleveland")
"""

from packages.audit.models import (
    ImmutableAuditRecord,
    AuditEventType,
    AuditSeverity,
)
from packages.audit.chain import AuditChain

__all__ = [
    "ImmutableAuditRecord",
    "AuditEventType",
    "AuditSeverity",
    "AuditChain",
]

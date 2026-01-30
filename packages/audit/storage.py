"""Audit storage backends.

Provides append-only storage implementations for audit records.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from packages.audit.models import (
    ImmutableAuditRecord,
    AuditEventType,
    AuditSeverity,
    ActorType,
    AuditQuery,
)

logger = logging.getLogger(__name__)


class FileAuditStorage:
    """File-based audit storage for development and small deployments.

    Stores records in JSONL (JSON Lines) format, one record per line.
    Each tenant gets its own file for isolation.

    WARNING: This is NOT suitable for high-volume production use.
    Use PostgresAuditStorage for production deployments.
    """

    def __init__(self, storage_path: str | Path):
        """Initialize file storage.

        Args:
            storage_path: Directory to store audit files
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        logger.info("FileAuditStorage initialized at %s", self.storage_path)

    def _tenant_file(self, tenant_id: str) -> Path:
        """Get the file path for a tenant's audit log."""
        # Sanitize tenant_id to prevent path traversal
        safe_id = "".join(c for c in tenant_id if c.isalnum() or c in "-_")
        return self.storage_path / f"audit_{safe_id}.jsonl"

    async def append(self, record: ImmutableAuditRecord) -> None:
        """Append a record to storage."""
        file_path = self._tenant_file(record.tenant_id)

        # Serialize record
        record_json = record.model_dump_json()

        # Append to file (atomic write with file locking would be better)
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(record_json + "\n")

        logger.debug(
            "Appended audit record: tenant=%s seq=%d",
            record.tenant_id,
            record.sequence_number,
        )

    async def get_latest(self, tenant_id: str) -> ImmutableAuditRecord | None:
        """Get the most recent record for a tenant."""
        file_path = self._tenant_file(tenant_id)

        if not file_path.exists():
            return None

        # Read last line
        last_line = None
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    last_line = line

        if not last_line:
            return None

        return ImmutableAuditRecord.model_validate_json(last_line)

    async def get_by_sequence(
        self, tenant_id: str, sequence: int
    ) -> ImmutableAuditRecord | None:
        """Get a record by sequence number."""
        file_path = self._tenant_file(tenant_id)

        if not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                record = ImmutableAuditRecord.model_validate_json(line)
                if record.sequence_number == sequence:
                    return record

        return None

    async def get_range(
        self,
        tenant_id: str,
        start_sequence: int,
        end_sequence: int,
    ) -> list[ImmutableAuditRecord]:
        """Get records in a sequence range."""
        file_path = self._tenant_file(tenant_id)

        if not file_path.exists():
            return []

        records = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                record = ImmutableAuditRecord.model_validate_json(line)
                if start_sequence <= record.sequence_number <= end_sequence:
                    records.append(record)

        return sorted(records, key=lambda r: r.sequence_number)

    async def get_all(
        self, tenant_id: str, limit: int = 10000
    ) -> list[ImmutableAuditRecord]:
        """Get all records for a tenant."""
        file_path = self._tenant_file(tenant_id)

        if not file_path.exists():
            return []

        records = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                records.append(ImmutableAuditRecord.model_validate_json(line))
                if len(records) >= limit:
                    break

        return sorted(records, key=lambda r: r.sequence_number)

    async def count(self, tenant_id: str) -> int:
        """Get total record count for a tenant."""
        file_path = self._tenant_file(tenant_id)

        if not file_path.exists():
            return 0

        count = 0
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    count += 1

        return count

    async def query(self, query: AuditQuery) -> list[ImmutableAuditRecord]:
        """Query audit records with filters."""
        all_records = await self.get_all(query.tenant_id)

        # Apply filters
        filtered = []
        for record in all_records:
            if query.event_types and record.event_type not in query.event_types:
                continue
            if query.actor_id and record.actor_id != query.actor_id:
                continue
            if query.resource_type and record.resource_type != query.resource_type:
                continue
            if query.resource_id and record.resource_id != query.resource_id:
                continue
            if query.start_time and record.timestamp < query.start_time:
                continue
            if query.end_time and record.timestamp > query.end_time:
                continue

            filtered.append(record)

        # Apply pagination
        start = query.offset
        end = start + query.limit
        return filtered[start:end]


class PostgresAuditStorage:
    """PostgreSQL-based audit storage for production.

    Uses the immutable_audit_log table with database-level
    immutability enforcement via triggers.
    """

    def __init__(self, connection_pool: Any):
        """Initialize PostgreSQL storage.

        Args:
            connection_pool: asyncpg connection pool
        """
        self.pool = connection_pool
        logger.info("PostgresAuditStorage initialized")

    async def append(self, record: ImmutableAuditRecord) -> None:
        """Append a record to storage."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO immutable_audit_log (
                    record_id, sequence_number, tenant_id, timestamp,
                    event_type, severity, actor_id, actor_type, actor_ip,
                    action, resource_type, resource_id, outcome, outcome_details,
                    payload, previous_hash, record_hash, environment,
                    api_version, correlation_id
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                    $11, $12, $13, $14, $15, $16, $17, $18, $19, $20
                )
                """,
                record.record_id,
                record.sequence_number,
                record.tenant_id,
                record.timestamp,
                record.event_type.value if isinstance(record.event_type, AuditEventType) else record.event_type,
                record.severity.value if isinstance(record.severity, AuditSeverity) else record.severity,
                record.actor_id,
                record.actor_type.value if isinstance(record.actor_type, ActorType) else record.actor_type,
                record.actor_ip,
                record.action,
                record.resource_type,
                record.resource_id,
                record.outcome,
                record.outcome_details,
                json.dumps(record.payload),
                record.previous_hash,
                record.record_hash,
                record.environment,
                record.api_version,
                record.correlation_id,
            )

    async def get_latest(self, tenant_id: str) -> ImmutableAuditRecord | None:
        """Get the most recent record for a tenant."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM immutable_audit_log
                WHERE tenant_id = $1
                ORDER BY sequence_number DESC
                LIMIT 1
                """,
                tenant_id,
            )

            if not row:
                return None

            return self._row_to_record(row)

    async def get_by_sequence(
        self, tenant_id: str, sequence: int
    ) -> ImmutableAuditRecord | None:
        """Get a record by sequence number."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM immutable_audit_log
                WHERE tenant_id = $1 AND sequence_number = $2
                """,
                tenant_id,
                sequence,
            )

            if not row:
                return None

            return self._row_to_record(row)

    async def get_range(
        self,
        tenant_id: str,
        start_sequence: int,
        end_sequence: int,
    ) -> list[ImmutableAuditRecord]:
        """Get records in a sequence range."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM immutable_audit_log
                WHERE tenant_id = $1
                  AND sequence_number >= $2
                  AND sequence_number <= $3
                ORDER BY sequence_number
                """,
                tenant_id,
                start_sequence,
                end_sequence,
            )

            return [self._row_to_record(row) for row in rows]

    async def get_all(
        self, tenant_id: str, limit: int = 10000
    ) -> list[ImmutableAuditRecord]:
        """Get all records for a tenant."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM immutable_audit_log
                WHERE tenant_id = $1
                ORDER BY sequence_number
                LIMIT $2
                """,
                tenant_id,
                limit,
            )

            return [self._row_to_record(row) for row in rows]

    async def count(self, tenant_id: str) -> int:
        """Get total record count for a tenant."""
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                """
                SELECT COUNT(*) FROM immutable_audit_log
                WHERE tenant_id = $1
                """,
                tenant_id,
            )
            return result or 0

    async def query(self, query: AuditQuery) -> list[ImmutableAuditRecord]:
        """Query audit records with filters."""
        conditions = ["tenant_id = $1"]
        params: list[Any] = [query.tenant_id]
        param_num = 2

        if query.event_types:
            placeholders = ", ".join(f"${i}" for i in range(param_num, param_num + len(query.event_types)))
            conditions.append(f"event_type IN ({placeholders})")
            params.extend(e.value for e in query.event_types)
            param_num += len(query.event_types)

        if query.actor_id:
            conditions.append(f"actor_id = ${param_num}")
            params.append(query.actor_id)
            param_num += 1

        if query.resource_type:
            conditions.append(f"resource_type = ${param_num}")
            params.append(query.resource_type)
            param_num += 1

        if query.resource_id:
            conditions.append(f"resource_id = ${param_num}")
            params.append(query.resource_id)
            param_num += 1

        if query.start_time:
            conditions.append(f"timestamp >= ${param_num}")
            params.append(query.start_time)
            param_num += 1

        if query.end_time:
            conditions.append(f"timestamp <= ${param_num}")
            params.append(query.end_time)
            param_num += 1

        where_clause = " AND ".join(conditions)

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT * FROM immutable_audit_log
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT ${param_num} OFFSET ${param_num + 1}
                """,
                *params,
                query.limit,
                query.offset,
            )

            return [self._row_to_record(row) for row in rows]

    def _row_to_record(self, row: Any) -> ImmutableAuditRecord:
        """Convert database row to record."""
        return ImmutableAuditRecord(
            record_id=str(row["record_id"]),
            sequence_number=row["sequence_number"],
            tenant_id=row["tenant_id"],
            timestamp=row["timestamp"],
            event_type=AuditEventType(row["event_type"]),
            severity=AuditSeverity(row["severity"]),
            actor_id=row["actor_id"],
            actor_type=ActorType(row["actor_type"]),
            actor_ip=str(row["actor_ip"]) if row["actor_ip"] else None,
            action=row["action"],
            resource_type=row["resource_type"],
            resource_id=row["resource_id"],
            outcome=row["outcome"],
            outcome_details=row["outcome_details"],
            payload=row["payload"] if isinstance(row["payload"], dict) else json.loads(row["payload"]),
            previous_hash=row["previous_hash"],
            record_hash=row["record_hash"],
            environment=row["environment"],
            api_version=row["api_version"],
            correlation_id=row["correlation_id"],
        )


# Factory function
def get_audit_storage(config: dict[str, Any] | None = None):
    """Get audit storage instance based on configuration."""
    if config and config.get("type") == "postgres":
        # Would need connection pool passed in
        raise NotImplementedError("PostgreSQL storage requires connection pool")

    # Default to file storage
    storage_path = config.get("path", "data/audit") if config else "data/audit"
    return FileAuditStorage(storage_path)

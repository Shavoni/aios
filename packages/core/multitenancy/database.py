"""Database-Level Tenant Isolation.

Provides true enterprise multi-tenancy with:
- Schema-per-tenant isolation
- Row-level security
- Tenant-scoped connections
- Automatic tenant context injection
- Encryption key management per tenant
"""

from __future__ import annotations

import os
import hashlib
import secrets
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from pathlib import Path
from typing import Any, Generator, TypeVar, Generic
from functools import wraps
import json
import threading

# For SQLAlchemy support (optional)
try:
    from sqlalchemy import create_engine, MetaData, Table, Column, String, DateTime, JSON, Boolean, Float, Integer, Text, ForeignKey, event, text
    from sqlalchemy.orm import sessionmaker, scoped_session, Session
    from sqlalchemy.pool import QueuePool
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False


class IsolationLevel(str, Enum):
    """Tenant isolation levels."""

    SHARED = "shared"  # Shared tables with tenant_id column
    SCHEMA = "schema"  # Separate schema per tenant
    DATABASE = "database"  # Separate database per tenant


@dataclass
class TenantConnection:
    """Connection configuration for a tenant."""

    tenant_id: str
    isolation_level: IsolationLevel = IsolationLevel.SHARED

    # Connection details
    database_url: str = ""
    schema_name: str = ""

    # Encryption
    encryption_key: str = ""
    encryption_enabled: bool = False

    # Pool settings
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30

    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "isolation_level": self.isolation_level.value,
            "database_url": self.database_url[:20] + "..." if self.database_url else "",
            "schema_name": self.schema_name,
            "encryption_enabled": self.encryption_enabled,
            "pool_size": self.pool_size,
            "created_at": self.created_at,
        }


@dataclass
class TenantEncryptionKey:
    """Encryption key for a tenant."""

    tenant_id: str
    key_id: str
    key_material: bytes  # Should be stored encrypted in production
    algorithm: str = "AES-256-GCM"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    expires_at: str | None = None
    is_active: bool = True

    @classmethod
    def generate(cls, tenant_id: str) -> TenantEncryptionKey:
        """Generate a new encryption key for a tenant."""
        return cls(
            tenant_id=tenant_id,
            key_id=secrets.token_hex(8),
            key_material=secrets.token_bytes(32),  # 256 bits
        )


class TenantContext:
    """Thread-local tenant context."""

    _local = threading.local()

    @classmethod
    def set_tenant(cls, tenant_id: str) -> None:
        """Set the current tenant context."""
        cls._local.tenant_id = tenant_id

    @classmethod
    def get_tenant(cls) -> str | None:
        """Get the current tenant ID."""
        return getattr(cls._local, "tenant_id", None)

    @classmethod
    def clear_tenant(cls) -> None:
        """Clear the tenant context."""
        cls._local.tenant_id = None

    @classmethod
    @contextmanager
    def tenant_scope(cls, tenant_id: str) -> Generator[str, None, None]:
        """Context manager for tenant-scoped operations."""
        previous = cls.get_tenant()
        cls.set_tenant(tenant_id)
        try:
            yield tenant_id
        finally:
            if previous:
                cls.set_tenant(previous)
            else:
                cls.clear_tenant()


def require_tenant(func):
    """Decorator to require tenant context."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        tenant_id = TenantContext.get_tenant()
        if not tenant_id:
            raise ValueError("No tenant context set. Use TenantContext.tenant_scope()")
        return func(*args, **kwargs)
    return wrapper


class TenantDatabaseManager:
    """Manages database connections and isolation for multiple tenants."""

    def __init__(
        self,
        default_database_url: str | None = None,
        isolation_level: IsolationLevel = IsolationLevel.SHARED,
        storage_path: Path | None = None,
    ):
        self._default_db_url = default_database_url or os.environ.get(
            "DATABASE_URL", "sqlite:///data/aios.db"
        )
        self._default_isolation = isolation_level
        self._storage_path = storage_path or Path("data/tenants/db")
        self._storage_path.mkdir(parents=True, exist_ok=True)

        # Connection pools per tenant
        self._engines: dict[str, Any] = {}
        self._sessions: dict[str, Any] = {}
        self._connections: dict[str, TenantConnection] = {}
        self._encryption_keys: dict[str, TenantEncryptionKey] = {}

        self._load_connections()

    def _load_connections(self) -> None:
        """Load tenant connection configs."""
        config_file = self._storage_path / "connections.json"
        if config_file.exists():
            try:
                data = json.loads(config_file.read_text())
                for tenant_id, conn_data in data.items():
                    self._connections[tenant_id] = TenantConnection(
                        tenant_id=tenant_id,
                        isolation_level=IsolationLevel(conn_data.get("isolation_level", "shared")),
                        database_url=conn_data.get("database_url", ""),
                        schema_name=conn_data.get("schema_name", ""),
                        encryption_enabled=conn_data.get("encryption_enabled", False),
                        pool_size=conn_data.get("pool_size", 5),
                    )
            except Exception:
                pass

    def _save_connections(self) -> None:
        """Save tenant connection configs."""
        config_file = self._storage_path / "connections.json"
        data = {}
        for tenant_id, conn in self._connections.items():
            data[tenant_id] = {
                "isolation_level": conn.isolation_level.value,
                "database_url": conn.database_url,
                "schema_name": conn.schema_name,
                "encryption_enabled": conn.encryption_enabled,
                "pool_size": conn.pool_size,
            }
        config_file.write_text(json.dumps(data, indent=2))

    # =========================================================================
    # Tenant Connection Management
    # =========================================================================

    def register_tenant(
        self,
        tenant_id: str,
        isolation_level: IsolationLevel | None = None,
        database_url: str | None = None,
        enable_encryption: bool = False,
    ) -> TenantConnection:
        """Register a new tenant with database configuration."""
        level = isolation_level or self._default_isolation

        # Generate schema name for schema isolation
        # Replace hyphens with underscores for valid SQL identifier
        schema_name = ""
        if level == IsolationLevel.SCHEMA:
            safe_id = tenant_id.replace("-", "_")
            schema_name = f"tenant_{safe_id}"

        # Generate database URL for database isolation
        db_url = database_url or ""
        if level == IsolationLevel.DATABASE and not db_url:
            # Create tenant-specific SQLite database
            db_url = f"sqlite:///{self._storage_path}/{tenant_id}.db"

        connection = TenantConnection(
            tenant_id=tenant_id,
            isolation_level=level,
            database_url=db_url or self._default_db_url,
            schema_name=schema_name,
            encryption_enabled=enable_encryption,
        )

        self._connections[tenant_id] = connection
        self._save_connections()

        # Generate encryption key if enabled
        if enable_encryption:
            self._encryption_keys[tenant_id] = TenantEncryptionKey.generate(tenant_id)

        # Initialize database resources
        self._initialize_tenant_db(connection)

        return connection

    def _initialize_tenant_db(self, connection: TenantConnection) -> None:
        """Initialize database resources for a tenant."""
        if not HAS_SQLALCHEMY:
            return

        # Create engine
        engine = create_engine(
            connection.database_url,
            poolclass=QueuePool,
            pool_size=connection.pool_size,
            max_overflow=connection.max_overflow,
            pool_timeout=connection.pool_timeout,
        )

        self._engines[connection.tenant_id] = engine

        # Create scoped session
        session_factory = sessionmaker(bind=engine)
        self._sessions[connection.tenant_id] = scoped_session(session_factory)

        # Create schema if schema isolation (not supported on SQLite)
        if connection.isolation_level == IsolationLevel.SCHEMA:
            # SQLite doesn't support schemas - skip schema creation
            if "sqlite" not in connection.database_url.lower():
                with engine.connect() as conn:
                    # Use quoted identifier for safety
                    conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{connection.schema_name}"'))
                    conn.commit()

    def get_connection(self, tenant_id: str) -> TenantConnection | None:
        """Get connection config for a tenant."""
        return self._connections.get(tenant_id)

    def get_engine(self, tenant_id: str):
        """Get SQLAlchemy engine for a tenant."""
        if not HAS_SQLALCHEMY:
            raise RuntimeError("SQLAlchemy not installed")

        if tenant_id not in self._engines:
            conn = self._connections.get(tenant_id)
            if conn:
                self._initialize_tenant_db(conn)

        return self._engines.get(tenant_id)

    def get_session(self, tenant_id: str):
        """Get SQLAlchemy session for a tenant."""
        if not HAS_SQLALCHEMY:
            raise RuntimeError("SQLAlchemy not installed")

        return self._sessions.get(tenant_id)

    @contextmanager
    def session_scope(self, tenant_id: str) -> Generator[Any, None, None]:
        """Context manager for tenant-scoped database session."""
        session = self.get_session(tenant_id)
        if not session:
            raise ValueError(f"No session for tenant {tenant_id}")

        sess = session()
        try:
            yield sess
            sess.commit()
        except Exception:
            sess.rollback()
            raise
        finally:
            sess.close()

    # =========================================================================
    # Row-Level Security Helpers
    # =========================================================================

    def add_tenant_filter(self, query, tenant_id: str, tenant_column: str = "tenant_id"):
        """Add tenant filter to a query for shared table isolation."""
        return query.filter_by(**{tenant_column: tenant_id})

    def inject_tenant_id(self, data: dict[str, Any], tenant_id: str) -> dict[str, Any]:
        """Inject tenant_id into data for inserts."""
        data["tenant_id"] = tenant_id
        return data

    # =========================================================================
    # Encryption
    # =========================================================================

    def get_encryption_key(self, tenant_id: str) -> TenantEncryptionKey | None:
        """Get encryption key for a tenant."""
        return self._encryption_keys.get(tenant_id)

    def encrypt_field(self, tenant_id: str, data: str) -> str:
        """Encrypt a field value for a tenant."""
        key = self.get_encryption_key(tenant_id)
        if not key or not key.is_active:
            return data

        # Simple encryption (use proper crypto in production)
        # This is a placeholder - use cryptography library in production
        import base64
        encrypted = base64.b64encode(data.encode()).decode()
        return f"ENC:{key.key_id}:{encrypted}"

    def decrypt_field(self, tenant_id: str, data: str) -> str:
        """Decrypt a field value for a tenant."""
        if not data.startswith("ENC:"):
            return data

        parts = data.split(":", 2)
        if len(parts) != 3:
            return data

        key_id, encrypted = parts[1], parts[2]
        key = self.get_encryption_key(tenant_id)

        if not key or key.key_id != key_id:
            raise ValueError("Invalid encryption key")

        # Simple decryption (use proper crypto in production)
        import base64
        return base64.b64decode(encrypted).decode()

    # =========================================================================
    # Cleanup
    # =========================================================================

    def close_tenant(self, tenant_id: str) -> None:
        """Close database connections for a tenant."""
        if tenant_id in self._engines:
            self._engines[tenant_id].dispose()
            del self._engines[tenant_id]

        if tenant_id in self._sessions:
            self._sessions[tenant_id].remove()
            del self._sessions[tenant_id]

    def close_all(self) -> None:
        """Close all database connections."""
        for tenant_id in list(self._engines.keys()):
            self.close_tenant(tenant_id)


class TenantAwareRepository:
    """Base class for tenant-aware data repositories."""

    def __init__(self, db_manager: TenantDatabaseManager):
        self._db = db_manager

    def _get_tenant_id(self) -> str:
        """Get current tenant ID from context."""
        tenant_id = TenantContext.get_tenant()
        if not tenant_id:
            raise ValueError("No tenant context")
        return tenant_id

    def _get_data_path(self, collection: str) -> Path:
        """Get tenant-specific data path for file-based storage."""
        tenant_id = self._get_tenant_id()
        path = Path(f"data/tenants/{tenant_id}/{collection}")
        path.mkdir(parents=True, exist_ok=True)
        return path


# File-based tenant isolation for simpler deployments
class FileTenantIsolation:
    """File-based tenant data isolation."""

    def __init__(self, base_path: Path | None = None):
        self._base_path = base_path or Path("data/tenants")
        self._base_path.mkdir(parents=True, exist_ok=True)

    def get_tenant_path(self, tenant_id: str) -> Path:
        """Get base path for a tenant's data."""
        path = self._base_path / tenant_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_collection_path(self, tenant_id: str, collection: str) -> Path:
        """Get path for a specific collection within a tenant."""
        path = self.get_tenant_path(tenant_id) / collection
        path.mkdir(parents=True, exist_ok=True)
        return path

    def read_json(self, tenant_id: str, collection: str, filename: str) -> dict | list | None:
        """Read JSON data for a tenant."""
        file_path = self.get_collection_path(tenant_id, collection) / f"{filename}.json"
        if file_path.exists():
            return json.loads(file_path.read_text())
        return None

    def write_json(self, tenant_id: str, collection: str, filename: str, data: dict | list) -> None:
        """Write JSON data for a tenant."""
        file_path = self.get_collection_path(tenant_id, collection) / f"{filename}.json"
        file_path.write_text(json.dumps(data, indent=2, default=str))

    def delete_json(self, tenant_id: str, collection: str, filename: str) -> bool:
        """Delete JSON data for a tenant."""
        file_path = self.get_collection_path(tenant_id, collection) / f"{filename}.json"
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def list_files(self, tenant_id: str, collection: str) -> list[str]:
        """List files in a tenant collection."""
        path = self.get_collection_path(tenant_id, collection)
        return [f.stem for f in path.glob("*.json")]

    def delete_tenant_data(self, tenant_id: str) -> bool:
        """Delete all data for a tenant."""
        import shutil
        path = self.get_tenant_path(tenant_id)
        if path.exists():
            shutil.rmtree(path)
            return True
        return False

    def get_tenant_size_bytes(self, tenant_id: str) -> int:
        """Get total size of tenant data in bytes."""
        path = self.get_tenant_path(tenant_id)
        if not path.exists():
            return 0

        total = 0
        for file_path in path.rglob("*"):
            if file_path.is_file():
                total += file_path.stat().st_size
        return total


# Singletons
_db_manager: TenantDatabaseManager | None = None
_file_isolation: FileTenantIsolation | None = None


def get_db_manager() -> TenantDatabaseManager:
    """Get database manager singleton."""
    global _db_manager
    if _db_manager is None:
        _db_manager = TenantDatabaseManager()
    return _db_manager


def get_file_isolation() -> FileTenantIsolation:
    """Get file isolation singleton."""
    global _file_isolation
    if _file_isolation is None:
        _file_isolation = FileTenantIsolation()
    return _file_isolation


__all__ = [
    "IsolationLevel",
    "TenantConnection",
    "TenantEncryptionKey",
    "TenantContext",
    "require_tenant",
    "TenantDatabaseManager",
    "TenantAwareRepository",
    "FileTenantIsolation",
    "get_db_manager",
    "get_file_isolation",
]

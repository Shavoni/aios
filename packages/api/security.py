"""Enterprise security module for AIOS API.

Provides authentication, authorization, rate limiting, and audit logging.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

# Configure structured logging
logging.basicConfig(level=logging.INFO)
audit_logger = logging.getLogger("aios.audit")
security_logger = logging.getLogger("aios.security")


# =============================================================================
# Enums and Constants
# =============================================================================


class Role(str, Enum):
    """User roles with hierarchical permissions."""

    VIEWER = "viewer"  # Read-only access
    USER = "user"  # Standard operations
    OPERATOR = "operator"  # Agent management
    ADMIN = "admin"  # Full access including policies
    SYSTEM = "system"  # Internal system calls


class Permission(str, Enum):
    """Granular permissions."""

    # Read permissions
    READ_AGENTS = "read:agents"
    READ_POLICIES = "read:policies"
    READ_KNOWLEDGE = "read:knowledge"

    # Write permissions
    WRITE_AGENTS = "write:agents"
    WRITE_POLICIES = "write:policies"
    WRITE_KNOWLEDGE = "write:knowledge"

    # Execute permissions
    EXECUTE_QUERY = "execute:query"
    EXECUTE_CLASSIFY = "execute:classify"
    EXECUTE_SIMULATE = "execute:simulate"

    # Admin permissions
    ADMIN_SYSTEM = "admin:system"
    ADMIN_RESET = "admin:reset"


# Role to permissions mapping
ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.VIEWER: {
        Permission.READ_AGENTS,
        Permission.READ_POLICIES,
        Permission.EXECUTE_CLASSIFY,
    },
    Role.USER: {
        Permission.READ_AGENTS,
        Permission.READ_POLICIES,
        Permission.READ_KNOWLEDGE,
        Permission.EXECUTE_QUERY,
        Permission.EXECUTE_CLASSIFY,
        Permission.EXECUTE_SIMULATE,
    },
    Role.OPERATOR: {
        Permission.READ_AGENTS,
        Permission.READ_POLICIES,
        Permission.READ_KNOWLEDGE,
        Permission.WRITE_AGENTS,
        Permission.WRITE_KNOWLEDGE,
        Permission.EXECUTE_QUERY,
        Permission.EXECUTE_CLASSIFY,
        Permission.EXECUTE_SIMULATE,
    },
    Role.ADMIN: {perm for perm in Permission},  # All permissions
    Role.SYSTEM: {perm for perm in Permission},  # All permissions
}


# =============================================================================
# Models
# =============================================================================


class APIKey(BaseModel):
    """API key configuration."""

    key_hash: str  # SHA-256 hash of the key
    name: str  # Human-readable name
    role: Role = Role.USER
    tenant_id: str | None = None
    department: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None
    enabled: bool = True
    rate_limit: int = 100  # Requests per minute
    last_used_at: datetime | None = None


class AuthenticatedUser(BaseModel):
    """Authenticated user context."""

    key_name: str
    role: Role
    tenant_id: str | None = None
    department: str | None = None
    permissions: set[Permission] = Field(default_factory=set)


class AuditEvent(BaseModel):
    """Audit log entry."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: str
    user: str
    role: str
    endpoint: str
    method: str
    tenant_id: str | None = None
    resource_id: str | None = None
    action: str
    status: str  # "success", "denied", "error"
    details: dict[str, Any] = Field(default_factory=dict)
    ip_address: str | None = None


# =============================================================================
# API Key Store (In production, use database)
# =============================================================================


class APIKeyStore:
    """Manages API keys with secure storage and validation."""

    def __init__(self):
        self._keys: dict[str, APIKey] = {}
        self._initialize_default_keys()

    def _initialize_default_keys(self):
        """Initialize default API keys for development."""
        import os

        if os.getenv("AIOS_ENV", "development") == "development":
            # Development keys - should be rotated in production
            dev_keys = [
                ("aios-admin-dev-key", "Development Admin", Role.ADMIN),
                ("aios-operator-dev-key", "Development Operator", Role.OPERATOR),
                ("aios-user-dev-key", "Development User", Role.USER),
            ]
            for key, name, role in dev_keys:
                self.register_key(key, name, role)
                security_logger.warning(
                    f"DEV MODE: Registered development API key '{name}' with role '{role}'"
                )

    def _hash_key(self, key: str) -> str:
        """Hash API key using SHA-256."""
        return hashlib.sha256(key.encode()).hexdigest()

    def register_key(
        self,
        raw_key: str,
        name: str,
        role: Role = Role.USER,
        tenant_id: str | None = None,
        department: str | None = None,
        expires_in_days: int | None = None,
        rate_limit: int = 100,
    ) -> str:
        """Register a new API key."""
        key_hash = self._hash_key(raw_key)

        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        self._keys[key_hash] = APIKey(
            key_hash=key_hash,
            name=name,
            role=role,
            tenant_id=tenant_id,
            department=department,
            expires_at=expires_at,
            rate_limit=rate_limit,
        )

        audit_logger.info(
            f"API key registered: name={name}, role={role}, tenant={tenant_id}"
        )
        return key_hash

    def validate_key(self, raw_key: str) -> APIKey | None:
        """Validate an API key and return its configuration."""
        key_hash = self._hash_key(raw_key)
        api_key = self._keys.get(key_hash)

        if not api_key:
            return None

        if not api_key.enabled:
            security_logger.warning(f"Disabled API key attempted: {api_key.name}")
            return None

        if api_key.expires_at and datetime.utcnow() > api_key.expires_at:
            security_logger.warning(f"Expired API key attempted: {api_key.name}")
            return None

        # Update last used timestamp
        api_key.last_used_at = datetime.utcnow()
        return api_key

    def revoke_key(self, key_hash: str) -> bool:
        """Revoke an API key."""
        if key_hash in self._keys:
            self._keys[key_hash].enabled = False
            audit_logger.info(f"API key revoked: {self._keys[key_hash].name}")
            return True
        return False

    def generate_key(self) -> str:
        """Generate a secure random API key."""
        return f"aios_{secrets.token_urlsafe(32)}"


# Global API key store
_api_key_store: APIKeyStore | None = None


def get_api_key_store() -> APIKeyStore:
    """Get or create the API key store singleton."""
    global _api_key_store
    if _api_key_store is None:
        _api_key_store = APIKeyStore()
    return _api_key_store


# =============================================================================
# Rate Limiter
# =============================================================================


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self):
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._cleanup_interval = 60  # seconds
        self._last_cleanup = time.time()

    def _cleanup(self):
        """Remove old request timestamps."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        cutoff = now - 60
        for key in list(self._requests.keys()):
            self._requests[key] = [t for t in self._requests[key] if t > cutoff]
            if not self._requests[key]:
                del self._requests[key]

        self._last_cleanup = now

    def is_allowed(self, key: str, limit: int) -> tuple[bool, int]:
        """Check if request is allowed under rate limit.

        Returns (allowed, remaining_requests).
        """
        self._cleanup()

        now = time.time()
        minute_ago = now - 60

        # Count recent requests
        recent = [t for t in self._requests[key] if t > minute_ago]
        self._requests[key] = recent

        if len(recent) >= limit:
            return False, 0

        self._requests[key].append(now)
        return True, limit - len(recent) - 1


# Global rate limiter
_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """Get or create the rate limiter singleton."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


# =============================================================================
# Authentication Dependencies
# =============================================================================

security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> AuthenticatedUser:
    """Authenticate request and return user context."""
    if not credentials:
        security_logger.warning(f"Missing auth header from {request.client.host}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    store = get_api_key_store()
    api_key = store.validate_key(token)

    if not api_key:
        security_logger.warning(
            f"Invalid API key from {request.client.host}: {token[:8]}..."
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check rate limit
    limiter = get_rate_limiter()
    allowed, remaining = limiter.is_allowed(api_key.key_hash, api_key.rate_limit)

    if not allowed:
        security_logger.warning(f"Rate limit exceeded for {api_key.name}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": "60", "X-RateLimit-Remaining": "0"},
        )

    # Build authenticated user
    permissions = ROLE_PERMISSIONS.get(api_key.role, set())

    return AuthenticatedUser(
        key_name=api_key.name,
        role=api_key.role,
        tenant_id=api_key.tenant_id,
        department=api_key.department,
        permissions=permissions,
    )


def require_permission(permission: Permission):
    """Dependency factory for permission-based authorization."""

    async def check_permission(
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        if permission not in user.permissions:
            security_logger.warning(
                f"Permission denied: {user.key_name} lacks {permission}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value} required",
            )
        return user

    return check_permission


def require_role(minimum_role: Role):
    """Dependency factory for role-based authorization."""
    role_hierarchy = [Role.VIEWER, Role.USER, Role.OPERATOR, Role.ADMIN, Role.SYSTEM]

    async def check_role(
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        user_level = role_hierarchy.index(user.role)
        required_level = role_hierarchy.index(minimum_role)

        if user_level < required_level:
            security_logger.warning(
                f"Role denied: {user.key_name} ({user.role}) needs {minimum_role}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient role: {minimum_role.value} or higher required",
            )
        return user

    return check_role


# =============================================================================
# Audit Logging
# =============================================================================


def log_audit_event(
    event_type: str,
    user: AuthenticatedUser | str,
    endpoint: str,
    method: str,
    action: str,
    status: str,
    request: Request | None = None,
    resource_id: str | None = None,
    details: dict[str, Any] | None = None,
):
    """Log an audit event."""
    if isinstance(user, AuthenticatedUser):
        user_name = user.key_name
        role = user.role.value
        tenant_id = user.tenant_id
    else:
        user_name = user
        role = "unknown"
        tenant_id = None

    event = AuditEvent(
        event_type=event_type,
        user=user_name,
        role=role,
        endpoint=endpoint,
        method=method,
        tenant_id=tenant_id,
        resource_id=resource_id,
        action=action,
        status=status,
        details=details or {},
        ip_address=request.client.host if request and request.client else None,
    )

    # Log as structured JSON for easy parsing
    audit_logger.info(event.model_dump_json())


def audit_endpoint(action: str):
    """Decorator for automatic endpoint audit logging."""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request: Request | None = kwargs.get("request")
            user: AuthenticatedUser | None = kwargs.get("user")

            try:
                result = await func(*args, **kwargs)
                log_audit_event(
                    event_type="api_call",
                    user=user or "anonymous",
                    endpoint=func.__name__,
                    method=request.method if request else "UNKNOWN",
                    action=action,
                    status="success",
                    request=request,
                )
                return result
            except HTTPException:
                log_audit_event(
                    event_type="api_call",
                    user=user or "anonymous",
                    endpoint=func.__name__,
                    method=request.method if request else "UNKNOWN",
                    action=action,
                    status="denied",
                    request=request,
                )
                raise
            except Exception as e:
                log_audit_event(
                    event_type="api_call",
                    user=user or "anonymous",
                    endpoint=func.__name__,
                    method=request.method if request else "UNKNOWN",
                    action=action,
                    status="error",
                    request=request,
                    details={"error": str(e)},
                )
                raise

        return wrapper

    return decorator


# =============================================================================
# Security Headers Middleware
# =============================================================================


async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)

    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

    # Cache control for API responses
    if request.url.path.startswith("/api") or request.url.path.startswith("/agents"):
        response.headers["Cache-Control"] = "no-store, max-age=0"

    return response


# =============================================================================
# Input Validation Utilities
# =============================================================================


def validate_tenant_id(tenant_id: str) -> str:
    """Validate tenant ID format."""
    import re

    if not re.match(r"^[a-zA-Z0-9_-]{1,64}$", tenant_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tenant_id format. Use alphanumeric characters, underscores, or hyphens (max 64 chars).",
        )
    return tenant_id


def validate_agent_id(agent_id: str) -> str:
    """Validate agent ID format."""
    import re

    if not re.match(r"^[a-zA-Z0-9_-]{1,64}$", agent_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid agent_id format. Use alphanumeric characters, underscores, or hyphens (max 64 chars).",
        )
    return agent_id


def sanitize_log_message(message: str, max_length: int = 500) -> str:
    """Sanitize message for logging to prevent log injection."""
    # Remove newlines and control characters
    sanitized = "".join(char for char in message if char.isprintable())
    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "...[truncated]"
    return sanitized


# =============================================================================
# File Upload Security
# =============================================================================

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {"txt", "pdf", "docx", "doc", "md", "json"}
ALLOWED_MIME_TYPES = {
    "text/plain",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "text/markdown",
    "application/json",
}


def validate_file_upload(filename: str, content: bytes, content_type: str | None):
    """Validate file upload for security."""
    # Check file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB.",
        )

    # Check extension
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{ext}' not allowed. Allowed: {ALLOWED_EXTENSIONS}",
        )

    # Check for null bytes (potential path traversal)
    if b"\x00" in content[:1024]:
        security_logger.warning(f"Null bytes detected in file upload: {filename}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file content detected.",
        )

    return True


__all__ = [
    "Role",
    "Permission",
    "APIKey",
    "AuthenticatedUser",
    "AuditEvent",
    "get_api_key_store",
    "get_rate_limiter",
    "get_current_user",
    "require_permission",
    "require_role",
    "log_audit_event",
    "audit_endpoint",
    "add_security_headers",
    "validate_tenant_id",
    "validate_agent_id",
    "validate_file_upload",
    "sanitize_log_message",
    "MAX_FILE_SIZE",
    "ALLOWED_EXTENSIONS",
]

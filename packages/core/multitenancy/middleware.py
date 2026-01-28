"""Tenant Middleware for Request-Level Context.

TENANT-001: Sets app.org_id via SET LOCAL for RLS enforcement.
"""

from __future__ import annotations

from typing import Callable, Any
from functools import wraps

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# SQLAlchemy imports (optional)
try:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False


class TenantMiddlewareError(Exception):
    """Error in tenant middleware."""
    pass


class MissingOrgIdError(TenantMiddlewareError):
    """Raised when org_id is missing from request."""

    def __init__(self, message: str = "Missing org_id in request"):
        self.message = message
        super().__init__(self.message)


def extract_org_id(request: Request) -> str | None:
    """Extract org_id from request.

    Checks in order:
    1. X-Tenant-ID header
    2. x-org-id header
    3. JWT claim (if available)
    4. Query parameter org_id

    Returns:
        org_id string or None if not found
    """
    # Check headers first
    org_id = request.headers.get("X-Tenant-ID")
    if org_id:
        return org_id

    org_id = request.headers.get("x-org-id")
    if org_id:
        return org_id

    # Check JWT (if authentication middleware has run)
    if hasattr(request.state, "user") and hasattr(request.state.user, "org_id"):
        return request.state.user.org_id

    # Check query params (last resort, not recommended for production)
    org_id = request.query_params.get("org_id")
    if org_id:
        return org_id

    return None


async def set_tenant_context_postgres(session: Any, org_id: str) -> None:
    """Set the tenant context in PostgreSQL session.

    Uses SET LOCAL to ensure the setting is transaction-scoped.

    Args:
        session: SQLAlchemy AsyncSession
        org_id: Tenant organization ID
    """
    if not HAS_SQLALCHEMY:
        raise RuntimeError("SQLAlchemy required for Postgres RLS")

    # SET LOCAL ensures the setting is cleared at end of transaction
    await session.execute(
        text("SET LOCAL app.org_id = :org_id"),
        {"org_id": org_id}
    )


async def clear_tenant_context_postgres(session: Any) -> None:
    """Clear the tenant context in PostgreSQL session."""
    if not HAS_SQLALCHEMY:
        return

    await session.execute(text("RESET app.org_id"))


class TenantMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for tenant context management.

    TENANT-001: Extracts org_id and sets it via SET LOCAL for RLS.
    Rejects requests without valid org_id.
    """

    # Paths that don't require tenant context
    EXCLUDED_PATHS = {
        "/health",
        "/healthz",
        "/ready",
        "/metrics",
        "/docs",
        "/openapi.json",
        "/redoc",
    }

    def __init__(self, app, get_session: Callable | None = None, require_tenant: bool = True):
        """Initialize tenant middleware.

        Args:
            app: FastAPI application
            get_session: Async callable that returns a database session
            require_tenant: If True, reject requests without org_id
        """
        super().__init__(app)
        self._get_session = get_session
        self._require_tenant = require_tenant

    async def dispatch(self, request: Request, call_next):
        """Process request and set tenant context."""
        # Skip excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        # Extract org_id
        org_id = extract_org_id(request)

        # Reject if missing and required
        if not org_id and self._require_tenant:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing org_id. Provide X-Tenant-ID header or authenticate."}
            )

        # Store in request state for application code
        request.state.org_id = org_id

        # Set database context if session factory provided
        if self._get_session and org_id:
            async with self._get_session() as session:
                await set_tenant_context_postgres(session, org_id)

                try:
                    response = await call_next(request)
                finally:
                    # Context is automatically cleared by transaction end
                    pass

                return response
        else:
            return await call_next(request)


def require_org_id(func: Callable) -> Callable:
    """Decorator to require org_id in request state.

    Use on route handlers that need tenant context.
    """
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        if not hasattr(request.state, "org_id") or not request.state.org_id:
            raise HTTPException(
                status_code=401,
                detail="Tenant context required for this operation"
            )
        return await func(request, *args, **kwargs)
    return wrapper


def get_current_org_id(request: Request) -> str:
    """Get the current org_id from request state.

    Raises:
        HTTPException: If org_id not set
    """
    if not hasattr(request.state, "org_id") or not request.state.org_id:
        raise HTTPException(
            status_code=401,
            detail="No tenant context available"
        )
    return request.state.org_id


class TenantScopedSession:
    """Context manager for tenant-scoped database sessions.

    Ensures SET LOCAL is called before any queries.
    """

    def __init__(self, session: Any, org_id: str):
        self._session = session
        self._org_id = org_id
        self._context_set = False

    async def __aenter__(self) -> Any:
        """Set tenant context and return session."""
        await set_tenant_context_postgres(self._session, self._org_id)
        self._context_set = True
        return self._session

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context is automatically cleared by transaction."""
        pass


__all__ = [
    "TenantMiddlewareError",
    "MissingOrgIdError",
    "extract_org_id",
    "set_tenant_context_postgres",
    "clear_tenant_context_postgres",
    "TenantMiddleware",
    "require_org_id",
    "get_current_org_id",
    "TenantScopedSession",
]

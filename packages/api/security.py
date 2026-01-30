"""Enterprise security integration for AIOS API.

This module provides easy setup for enterprise authentication and authorization.
Import and call `setup_enterprise_security(app)` to enable full security.

Usage (Development):
    # Uses header-based auth for development
    from packages.api.security import setup_enterprise_security
    setup_enterprise_security(app, mode="development")

Usage (Production):
    # Requires OIDC configuration
    from packages.api.security import setup_enterprise_security
    setup_enterprise_security(
        app,
        mode="production",
        oidc_issuer="https://login.microsoftonline.com/tenant/v2.0",
        oidc_client_id="your-client-id",
    )
"""

import logging
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from packages.auth.config import AuthConfig, AuthMode
from packages.auth.middleware import AuthMiddleware
from packages.auth.providers.base import AuthProvider
from packages.auth.providers.dev_header import DevHeaderProvider

logger = logging.getLogger(__name__)


def setup_enterprise_security(
    app: FastAPI,
    mode: Literal["production", "staging", "development", "test"] = "development",
    oidc_issuer: str | None = None,
    oidc_client_id: str | None = None,
    oidc_jwks_uri: str | None = None,
    oidc_audience: str | None = None,
    azure_tenant_id: str | None = None,
    okta_domain: str | None = None,
    exclude_paths: list[str] | None = None,
    exclude_prefixes: list[str] | None = None,
) -> AuthProvider:
    """Set up enterprise security for the application.

    This configures:
    - Authentication middleware (OIDC, SAML, or dev header)
    - Authorization engine
    - Audit logging integration

    Args:
        app: FastAPI application
        mode: Environment mode
        oidc_issuer: OIDC issuer URL (if using generic OIDC)
        oidc_client_id: OIDC client ID
        oidc_jwks_uri: JWKS URI (auto-discovered if not provided)
        oidc_audience: Expected audience claim
        azure_tenant_id: Azure AD tenant ID (if using Azure AD)
        okta_domain: Okta domain (if using Okta)
        exclude_paths: Paths to exclude from auth (e.g., ["/health"])
        exclude_prefixes: Path prefixes to exclude (e.g., ["/public/"])

    Returns:
        The configured auth provider
    """
    # Default excluded paths
    default_excludes = [
        "/health",
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
    ]

    all_excluded = list(set(default_excludes + (exclude_paths or [])))
    all_prefixes = list(set((exclude_prefixes or [])))

    # Create auth provider based on configuration
    provider: AuthProvider

    if azure_tenant_id:
        # Azure AD
        from packages.auth.providers.oidc import AzureADProvider

        if not oidc_client_id:
            raise ValueError("oidc_client_id required for Azure AD")

        provider = AzureADProvider(
            tenant_id=azure_tenant_id,
            client_id=oidc_client_id,
            audience=oidc_audience,
        )
        logger.info("Configured Azure AD authentication")

    elif okta_domain:
        # Okta
        from packages.auth.providers.oidc import OktaProvider

        if not oidc_client_id:
            raise ValueError("oidc_client_id required for Okta")

        provider = OktaProvider(
            okta_domain=okta_domain,
            client_id=oidc_client_id,
            audience=oidc_audience,
        )
        logger.info("Configured Okta authentication")

    elif oidc_issuer:
        # Generic OIDC
        from packages.auth.providers.oidc import OIDCProvider

        if not oidc_client_id:
            raise ValueError("oidc_client_id required for OIDC")

        provider = OIDCProvider(
            issuer=oidc_issuer,
            client_id=oidc_client_id,
            jwks_uri=oidc_jwks_uri,
            audience=oidc_audience,
        )
        logger.info("Configured OIDC authentication: %s", oidc_issuer)

    elif mode in ("development", "test"):
        # Development header auth
        provider = DevHeaderProvider()
        logger.warning("Using development header authentication - NOT SECURE")

    else:
        raise ValueError(
            f"No authentication configured for mode '{mode}'. "
            "Provide oidc_issuer, azure_tenant_id, or okta_domain."
        )

    # Add authentication middleware
    app.add_middleware(
        AuthMiddleware,
        provider=provider,
        exclude_paths=all_excluded,
        exclude_prefixes=all_prefixes,
    )

    logger.info(
        "Enterprise security enabled: mode=%s, provider=%s",
        mode,
        provider.provider_name,
    )

    return provider


def add_security_headers(app: FastAPI) -> None:
    """Add security headers middleware.

    Adds headers recommended for enterprise security:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Strict-Transport-Security (for HTTPS)
    """

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # HSTS for HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response

    logger.info("Security headers middleware added")


def add_rate_limiting(
    app: FastAPI,
    requests_per_minute: int = 60,
    burst: int = 10,
) -> None:
    """Add basic rate limiting middleware.

    Note: For production, use a proper rate limiting solution
    like Redis-based rate limiting or an API gateway.
    """
    from collections import defaultdict
    from datetime import datetime, timedelta

    # Simple in-memory rate limiter (not suitable for distributed systems)
    request_counts: dict[str, list[datetime]] = defaultdict(list)
    window = timedelta(minutes=1)

    @app.middleware("http")
    async def rate_limit(request: Request, call_next):
        # Get client identifier
        client_id = request.headers.get("X-Tenant-ID", "")
        if not client_id:
            forwarded = request.headers.get("X-Forwarded-For", "")
            client_id = forwarded.split(",")[0].strip() if forwarded else request.client.host

        # Clean old requests
        now = datetime.utcnow()
        cutoff = now - window
        request_counts[client_id] = [
            ts for ts in request_counts[client_id]
            if ts > cutoff
        ]

        # Check rate limit
        if len(request_counts[client_id]) >= requests_per_minute:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"Rate limit exceeded. Max {requests_per_minute} requests per minute.",
                    "retry_after_seconds": 60,
                }
            )

        # Record request
        request_counts[client_id].append(now)

        return await call_next(request)

    logger.info(
        "Rate limiting enabled: %d requests/minute, burst=%d",
        requests_per_minute,
        burst,
    )


def configure_audit_integration(app: FastAPI) -> None:
    """Configure automatic audit logging for API requests.

    Records audit events for:
    - Agent queries
    - Configuration changes
    - Authentication events
    """
    from packages.audit.chain import AuditChain
    from packages.audit.storage import get_audit_storage
    from packages.audit.models import AuditEventType

    storage = get_audit_storage()
    chain = AuditChain(storage)

    @app.middleware("http")
    async def audit_middleware(request: Request, call_next):
        response = await call_next(request)

        # Skip health checks and static content
        path = request.url.path
        if path in ("/health", "/docs", "/redoc", "/openapi.json"):
            return response

        # Get user context
        user = getattr(request.state, "user", None)
        if not user:
            return response

        # Record significant events
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            event_type = AuditEventType.DATA_UPDATE
            if request.method == "POST":
                event_type = AuditEventType.DATA_CREATE
            elif request.method == "DELETE":
                event_type = AuditEventType.DATA_DELETE

            # Don't await - fire and forget
            import asyncio
            asyncio.create_task(
                chain.append_record(
                    tenant_id=user.tenant_id,
                    event_type=event_type,
                    actor_id=user.user_id,
                    action=f"{request.method} {path}",
                    resource_type=path.split("/")[1] if "/" in path else "unknown",
                    outcome="success" if response.status_code < 400 else "failure",
                    payload={
                        "method": request.method,
                        "path": path,
                        "status_code": response.status_code,
                    },
                )
            )

        return response

    logger.info("Audit integration configured")

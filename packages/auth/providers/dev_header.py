"""Development-only header-based authentication.

WARNING: This provider is NOT SECURE and must NEVER be used in production.
It exists only to simplify development and testing workflows.

In development mode, this provider accepts:
- X-Tenant-ID: Tenant identifier
- X-User-ID: User identifier (optional, defaults to "dev-user")
- X-User-Role: User role (optional, defaults to "developer")
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from packages.auth.models import (
    AuthenticatedUser,
    AuthenticationError,
    MissingTokenError,
    TokenClaims,
)
from packages.auth.providers.base import AuthProvider

logger = logging.getLogger(__name__)


class DevHeaderProvider(AuthProvider):
    """Development-only header-based authentication.

    SECURITY WARNING:
    This provider trusts client-provided headers without verification.
    It must NEVER be enabled in production environments.

    Usage in development:
        curl -H "X-Tenant-ID: cleveland" -H "X-User-ID: dev@test.com" ...
    """

    def __init__(
        self,
        tenant_allowlist: list[str] | None = None,
        default_roles: list[str] | None = None,
    ):
        """Initialize dev header provider.

        Args:
            tenant_allowlist: If set, only these tenant IDs are allowed
            default_roles: Default roles to assign (default: ["developer"])
        """
        self.tenant_allowlist = tenant_allowlist
        self.default_roles = default_roles or ["developer"]

        # Log prominent warning
        logger.warning(
            "\n"
            "╔══════════════════════════════════════════════════════════════╗\n"
            "║  WARNING: DevHeaderProvider is ACTIVE                        ║\n"
            "║  This authentication method is NOT SECURE.                   ║\n"
            "║  Ensure AIOS_AUTH_MODE != 'production' in your environment.  ║\n"
            "╚══════════════════════════════════════════════════════════════╝"
        )

    @property
    def provider_name(self) -> str:
        return "dev_header"

    @property
    def is_secure(self) -> bool:
        return False  # NEVER secure

    async def authenticate(self, request: Any) -> AuthenticatedUser:
        """Authenticate using request headers.

        Required headers:
        - X-Tenant-ID: Tenant identifier

        Optional headers:
        - X-User-ID: User identifier (default: "dev-user")
        - X-User-Role: Comma-separated roles (default: ["developer"])
        - X-User-Email: User email
        - X-User-Department: User department
        """
        # Extract tenant ID (required)
        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id:
            raise MissingTokenError()

        # Validate against allowlist if configured
        if self.tenant_allowlist and tenant_id not in self.tenant_allowlist:
            raise AuthenticationError(
                f"Tenant '{tenant_id}' not in development allowlist",
                code="tenant_not_allowed"
            )

        # Extract optional headers
        user_id = request.headers.get("X-User-ID", "dev-user")
        roles_header = request.headers.get("X-User-Role", "")
        roles = [r.strip() for r in roles_header.split(",") if r.strip()]
        if not roles:
            roles = self.default_roles

        email = request.headers.get("X-User-Email", f"{user_id}@dev.local")
        department = request.headers.get("X-User-Department", "Development")

        # Create authenticated user
        now = datetime.utcnow()
        return AuthenticatedUser(
            user_id=user_id,
            tenant_id=tenant_id,
            email=email,
            name=user_id,
            roles=roles,
            groups=["dev-group"],
            department=department,
            token_exp=now + timedelta(hours=24),  # Long expiry for dev
            token_iat=now,
            auth_provider=self.provider_name,
            auth_method="header",
        )

    async def validate_token(self, token: str) -> TokenClaims:
        """Not applicable for header auth - raises error."""
        raise NotImplementedError(
            "DevHeaderProvider does not use tokens. "
            "Use authenticate() with request object instead."
        )


class DevHeaderWarning:
    """Utility to check and warn about dev auth usage."""

    @staticmethod
    def check_environment():
        """Check if dev auth is being used inappropriately."""
        import os

        mode = os.getenv("AIOS_AUTH_MODE", "development").lower()
        allow_header = os.getenv("AIOS_ALLOW_HEADER_AUTH", "false").lower() == "true"

        if mode == "production" and allow_header:
            raise RuntimeError(
                "CRITICAL SECURITY ERROR: Header authentication is enabled "
                "in production mode. This is a severe security vulnerability. "
                "Set AIOS_ALLOW_HEADER_AUTH=false or configure OIDC/SAML."
            )

        if mode in ("staging", "production") and allow_header:
            logger.critical(
                "SECURITY WARNING: Header authentication is enabled in %s mode. "
                "This should only be used for development/testing.",
                mode
            )

"""Authentication data models.

Core identity models for verified user context throughout AIOS.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TokenClaims(BaseModel):
    """Standard JWT claims with custom AIOS extensions.

    Standard claims (RFC 7519):
    - sub: Subject (user identifier)
    - iss: Issuer (IdP URL)
    - aud: Audience (this application)
    - exp: Expiration timestamp
    - iat: Issued at timestamp
    - nbf: Not before timestamp

    Custom AIOS claims:
    - tenant_id: Organization/tenant identifier
    - roles: User roles within the tenant
    - groups: Group memberships
    - department: User's department
    """

    # Standard claims
    sub: str = Field(description="Subject - unique user identifier")
    iss: str = Field(description="Issuer - IdP URL")
    aud: str | list[str] = Field(description="Audience - intended recipient(s)")
    exp: int = Field(description="Expiration time (Unix timestamp)")
    iat: int = Field(description="Issued at time (Unix timestamp)")
    nbf: int | None = Field(default=None, description="Not before time")
    jti: str | None = Field(default=None, description="JWT ID - unique identifier")

    # Custom AIOS claims
    tenant_id: str = Field(description="Tenant/organization identifier")
    roles: list[str] = Field(default_factory=list, description="User roles")
    groups: list[str] = Field(default_factory=list, description="Group memberships")
    department: str | None = Field(default=None, description="User's department")
    email: str | None = Field(default=None, description="User's email")
    name: str | None = Field(default=None, description="User's display name")

    # Additional claims (catch-all for IdP-specific)
    extra: dict[str, Any] = Field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.utcnow().timestamp() > self.exp

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles

    def has_any_role(self, roles: list[str]) -> bool:
        """Check if user has any of the specified roles."""
        return any(role in self.roles for role in roles)


class AuthenticatedUser(BaseModel):
    """Verified user identity from IdP.

    This is the canonical user context passed throughout AIOS
    after authentication. It represents a verified identity,
    not a raw token.
    """

    # Core identity
    user_id: str = Field(description="Unique user identifier")
    tenant_id: str = Field(description="Verified tenant identifier")
    email: str | None = Field(default=None, description="User's email")
    name: str | None = Field(default=None, description="User's display name")

    # Authorization context
    roles: list[str] = Field(default_factory=list, description="Assigned roles")
    groups: list[str] = Field(default_factory=list, description="Group memberships")
    department: str = Field(default="General", description="User's department")

    # Token metadata
    token_exp: datetime = Field(description="When the token expires")
    token_iat: datetime = Field(description="When the token was issued")

    # Auth provider info
    auth_provider: str = Field(description="Provider: 'oidc', 'saml', 'dev_header'")
    auth_method: str = Field(default="bearer", description="Method: 'bearer', 'cookie', 'header'")

    # Session info
    session_id: str | None = Field(default=None, description="Session identifier")

    @classmethod
    def from_claims(cls, claims: TokenClaims, provider: str) -> "AuthenticatedUser":
        """Create AuthenticatedUser from validated token claims."""
        return cls(
            user_id=claims.sub,
            tenant_id=claims.tenant_id,
            email=claims.email,
            name=claims.name,
            roles=claims.roles,
            groups=claims.groups,
            department=claims.department or "General",
            token_exp=datetime.fromtimestamp(claims.exp),
            token_iat=datetime.fromtimestamp(claims.iat),
            auth_provider=provider,
            session_id=claims.jti,
        )

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission.

        This is a placeholder - actual permission resolution
        should go through the authz package.
        """
        # Admin role has all permissions
        if "admin" in self.roles or "tenant_admin" in self.roles:
            return True
        # Otherwise, delegate to authz engine
        return False


class AuthenticationError(Exception):
    """Raised when authentication fails."""

    def __init__(self, message: str, code: str = "auth_failed"):
        self.message = message
        self.code = code
        super().__init__(message)


class TokenExpiredError(AuthenticationError):
    """Raised when a token has expired."""

    def __init__(self):
        super().__init__("Token has expired", "token_expired")


class InvalidTokenError(AuthenticationError):
    """Raised when a token is invalid."""

    def __init__(self, reason: str = "Token validation failed"):
        super().__init__(reason, "invalid_token")


class MissingTokenError(AuthenticationError):
    """Raised when no token is provided."""

    def __init__(self):
        super().__init__("No authentication token provided", "missing_token")


class InsufficientPermissionsError(AuthenticationError):
    """Raised when user lacks required permissions."""

    def __init__(self, required: str):
        super().__init__(
            f"Insufficient permissions. Required: {required}",
            "insufficient_permissions"
        )

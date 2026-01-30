"""Authentication configuration.

Environment-aware configuration that enforces security
requirements based on deployment mode.
"""

import os
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class AuthMode(str, Enum):
    """Authentication mode based on environment."""

    PRODUCTION = "production"
    STAGING = "staging"
    DEVELOPMENT = "development"
    TEST = "test"


class AuthConfig(BaseModel):
    """Authentication configuration.

    Security rules:
    - Production: OIDC or SAML required, header auth forbidden
    - Staging: OIDC/SAML preferred, header auth allowed with warning
    - Development: Header auth allowed for convenience
    - Test: Any auth method allowed
    """

    mode: AuthMode = Field(
        default=AuthMode.DEVELOPMENT,
        description="Environment mode determining auth requirements"
    )

    # OIDC Configuration
    oidc_issuer: str | None = Field(
        default=None,
        description="OIDC issuer URL (e.g., https://login.microsoftonline.com/tenant)"
    )
    oidc_client_id: str | None = Field(
        default=None,
        description="OIDC client/application ID"
    )
    oidc_client_secret: str | None = Field(
        default=None,
        description="OIDC client secret (for confidential clients)"
    )
    oidc_jwks_uri: str | None = Field(
        default=None,
        description="JWKS URI for token validation (auto-discovered if not set)"
    )
    oidc_audience: str | None = Field(
        default=None,
        description="Expected audience claim in tokens"
    )
    oidc_scopes: list[str] = Field(
        default=["openid", "profile", "email"],
        description="OAuth scopes to request"
    )

    # SAML Configuration
    saml_idp_metadata_url: str | None = Field(
        default=None,
        description="SAML IdP metadata URL"
    )
    saml_sp_entity_id: str | None = Field(
        default=None,
        description="Service Provider entity ID"
    )
    saml_sp_acs_url: str | None = Field(
        default=None,
        description="Assertion Consumer Service URL"
    )
    saml_certificate_path: str | None = Field(
        default=None,
        description="Path to SP certificate for signing"
    )

    # Development header auth (NEVER in production)
    allow_header_auth: bool = Field(
        default=False,
        description="Allow X-Tenant-ID header auth (dev only)"
    )
    header_auth_tenant_allowlist: list[str] = Field(
        default_factory=list,
        description="Allowed tenant IDs for header auth"
    )

    # Token settings
    token_clock_skew_seconds: int = Field(
        default=30,
        description="Allowed clock skew for token validation"
    )
    token_cache_ttl_seconds: int = Field(
        default=300,
        description="TTL for JWKS cache"
    )

    # Session settings
    session_timeout_minutes: int = Field(
        default=60,
        description="Session timeout in minutes"
    )

    @model_validator(mode="after")
    def validate_production_security(self) -> "AuthConfig":
        """Enforce security requirements for production."""
        if self.mode == AuthMode.PRODUCTION:
            # Header auth is NEVER allowed in production
            if self.allow_header_auth:
                raise ValueError(
                    "SECURITY ERROR: Header-based authentication is forbidden "
                    "in production. Configure OIDC or SAML."
                )

            # Must have either OIDC or SAML configured
            has_oidc = self.oidc_issuer is not None
            has_saml = self.saml_idp_metadata_url is not None

            if not (has_oidc or has_saml):
                raise ValueError(
                    "SECURITY ERROR: Production mode requires OIDC or SAML "
                    "authentication. Set oidc_issuer or saml_idp_metadata_url."
                )

        return self

    @classmethod
    def from_env(cls) -> "AuthConfig":
        """Create configuration from environment variables."""
        mode_str = os.getenv("AIOS_AUTH_MODE", "development").lower()
        mode = AuthMode(mode_str)

        return cls(
            mode=mode,
            # OIDC
            oidc_issuer=os.getenv("AIOS_OIDC_ISSUER"),
            oidc_client_id=os.getenv("AIOS_OIDC_CLIENT_ID"),
            oidc_client_secret=os.getenv("AIOS_OIDC_CLIENT_SECRET"),
            oidc_jwks_uri=os.getenv("AIOS_OIDC_JWKS_URI"),
            oidc_audience=os.getenv("AIOS_OIDC_AUDIENCE"),
            # SAML
            saml_idp_metadata_url=os.getenv("AIOS_SAML_IDP_METADATA"),
            saml_sp_entity_id=os.getenv("AIOS_SAML_SP_ENTITY_ID"),
            saml_sp_acs_url=os.getenv("AIOS_SAML_SP_ACS_URL"),
            # Dev auth
            allow_header_auth=os.getenv("AIOS_ALLOW_HEADER_AUTH", "false").lower() == "true",
        )

    def get_provider_type(self) -> Literal["oidc", "saml", "header", "none"]:
        """Determine which auth provider to use."""
        if self.oidc_issuer:
            return "oidc"
        elif self.saml_idp_metadata_url:
            return "saml"
        elif self.allow_header_auth and self.mode != AuthMode.PRODUCTION:
            return "header"
        else:
            return "none"

    def is_secure(self) -> bool:
        """Check if configuration meets security requirements."""
        provider = self.get_provider_type()
        return provider in ("oidc", "saml")

"""API configuration via pydantic-settings."""

from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_prefix="AIOS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # API configuration
    api_title: str = "AIOS Governance API"
    api_version: str = "1.0.0"

    # CORS origins
    cors_origins: list[str] = ["*"]

    # === ENTERPRISE AUTH SETTINGS ===
    auth_mode: Literal["production", "staging", "development", "test"] = "development"

    # OIDC configuration
    oidc_issuer: str | None = None
    oidc_client_id: str | None = None
    oidc_client_secret: str | None = None
    oidc_jwks_uri: str | None = None
    oidc_audience: str | None = None

    # SAML configuration
    saml_idp_metadata: str | None = None
    saml_sp_entity_id: str | None = None
    saml_sp_acs_url: str | None = None

    # Development auth (NEVER enable in production)
    allow_header_auth: bool = True  # Default True for dev, enforce False in production

    # === GROUNDING SETTINGS ===
    grounding_enabled: bool = True
    grounding_min_score: float = 0.5
    grounding_require_verified: bool = False
    grounding_warn_threshold: float = 0.7

    # === AUDIT SETTINGS ===
    audit_enabled: bool = True
    audit_storage_type: Literal["file", "postgres"] = "file"
    audit_storage_path: str = "data/audit"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.auth_mode == "production"

    @property
    def auth_config(self):
        """Get auth configuration object."""
        from packages.auth.config import AuthConfig, AuthMode

        return AuthConfig(
            mode=AuthMode(self.auth_mode),
            oidc_issuer=self.oidc_issuer,
            oidc_client_id=self.oidc_client_id,
            oidc_client_secret=self.oidc_client_secret,
            oidc_jwks_uri=self.oidc_jwks_uri,
            oidc_audience=self.oidc_audience,
            saml_idp_metadata_url=self.saml_idp_metadata,
            saml_sp_entity_id=self.saml_sp_entity_id,
            saml_sp_acs_url=self.saml_sp_acs_url,
            allow_header_auth=self.allow_header_auth and not self.is_production,
        )

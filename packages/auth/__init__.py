"""HAAIS AIOS Authentication Package.

Enterprise-grade authentication supporting:
- OIDC (OpenID Connect) integration
- SAML 2.0 integration
- JWT validation with JWKS
- Environment-gated development auth

Usage:
    from packages.auth import get_auth_provider, AuthMiddleware

    # Get configured provider
    provider = get_auth_provider(settings)

    # Add middleware to FastAPI
    app.add_middleware(AuthMiddleware, provider=provider)
"""

from packages.auth.config import AuthConfig, AuthMode
from packages.auth.models import AuthenticatedUser, TokenClaims
from packages.auth.middleware import AuthMiddleware
from packages.auth.providers.base import AuthProvider

__all__ = [
    "AuthConfig",
    "AuthMode",
    "AuthenticatedUser",
    "TokenClaims",
    "AuthMiddleware",
    "AuthProvider",
]


def get_auth_provider(config: AuthConfig) -> AuthProvider:
    """Get the appropriate auth provider based on configuration."""
    from packages.auth.providers.dev_header import DevHeaderProvider
    from packages.auth.providers.oidc import OIDCProvider

    if config.mode == AuthMode.DEVELOPMENT and config.allow_header_auth:
        return DevHeaderProvider()
    elif config.oidc_issuer:
        return OIDCProvider(
            issuer=config.oidc_issuer,
            client_id=config.oidc_client_id,
            jwks_uri=config.oidc_jwks_uri,
        )
    else:
        raise ValueError("No valid auth provider configured")

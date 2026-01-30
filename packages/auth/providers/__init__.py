"""Authentication providers.

Pluggable authentication backends:
- OIDC: OpenID Connect (Azure AD, Okta, Auth0, etc.)
- SAML: SAML 2.0 (Enterprise SSO)
- DevHeader: Development-only header-based auth
"""

from packages.auth.providers.base import AuthProvider
from packages.auth.providers.dev_header import DevHeaderProvider

__all__ = [
    "AuthProvider",
    "DevHeaderProvider",
]

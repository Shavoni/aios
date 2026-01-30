"""Abstract base class for authentication providers.

All auth providers must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import Any

from packages.auth.models import AuthenticatedUser, TokenClaims


class AuthProvider(ABC):
    """Abstract authentication provider.

    Implementations:
    - OIDCProvider: OpenID Connect with JWT validation
    - SAMLProvider: SAML 2.0 assertion handling
    - DevHeaderProvider: Development-only header auth
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider identifier (e.g., 'oidc', 'saml')."""
        pass

    @property
    @abstractmethod
    def is_secure(self) -> bool:
        """Return whether this provider is secure for production."""
        pass

    @abstractmethod
    async def authenticate(self, request: Any) -> AuthenticatedUser:
        """Authenticate a request and return verified user.

        Args:
            request: The incoming HTTP request (FastAPI Request object)

        Returns:
            AuthenticatedUser with verified identity

        Raises:
            AuthenticationError: If authentication fails
            MissingTokenError: If no credentials provided
            InvalidTokenError: If credentials are invalid
            TokenExpiredError: If credentials are expired
        """
        pass

    @abstractmethod
    async def validate_token(self, token: str) -> TokenClaims:
        """Validate a token and extract claims.

        Args:
            token: The raw token string (JWT, SAML assertion, etc.)

        Returns:
            TokenClaims with validated claims

        Raises:
            InvalidTokenError: If token is invalid
            TokenExpiredError: If token is expired
        """
        pass

    async def refresh_token(self, refresh_token: str) -> tuple[str, str]:
        """Refresh an access token (if supported).

        Args:
            refresh_token: The refresh token

        Returns:
            Tuple of (new_access_token, new_refresh_token)

        Raises:
            NotImplementedError: If provider doesn't support refresh
            InvalidTokenError: If refresh token is invalid
        """
        raise NotImplementedError(
            f"{self.provider_name} does not support token refresh"
        )

    async def logout(self, user: AuthenticatedUser) -> str | None:
        """Perform logout and return redirect URL if applicable.

        Args:
            user: The user to log out

        Returns:
            Logout redirect URL, or None if not applicable
        """
        return None

    def get_login_url(self, state: str | None = None) -> str | None:
        """Get the login URL for this provider (if applicable).

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Login URL, or None if not applicable
        """
        return None

"""OpenID Connect (OIDC) authentication provider.

Supports Azure AD, Okta, Auth0, Google, and any OIDC-compliant IdP.
"""

import logging
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

import httpx

from packages.auth.models import (
    AuthenticatedUser,
    AuthenticationError,
    InvalidTokenError,
    MissingTokenError,
    TokenClaims,
    TokenExpiredError,
)
from packages.auth.providers.base import AuthProvider

logger = logging.getLogger(__name__)


class OIDCProvider(AuthProvider):
    """OpenID Connect authentication provider.

    Validates JWT tokens against the IdP's JWKS endpoint.
    Supports automatic JWKS key rotation and caching.

    Usage:
        provider = OIDCProvider(
            issuer="https://login.microsoftonline.com/tenant-id/v2.0",
            client_id="your-client-id",
        )
    """

    def __init__(
        self,
        issuer: str,
        client_id: str,
        jwks_uri: str | None = None,
        audience: str | None = None,
        clock_skew_seconds: int = 30,
        cache_ttl_seconds: int = 300,
        tenant_claim: str = "tenant_id",
        roles_claim: str = "roles",
    ):
        """Initialize OIDC provider.

        Args:
            issuer: OIDC issuer URL (e.g., https://login.microsoftonline.com/tenant)
            client_id: OAuth client/application ID
            jwks_uri: JWKS URI (auto-discovered if not provided)
            audience: Expected audience claim (defaults to client_id)
            clock_skew_seconds: Allowed clock skew for token validation
            cache_ttl_seconds: TTL for JWKS cache
            tenant_claim: Claim name containing tenant ID
            roles_claim: Claim name containing user roles
        """
        self.issuer = issuer.rstrip("/")
        self.client_id = client_id
        self.audience = audience or client_id
        self.clock_skew = clock_skew_seconds
        self.cache_ttl = cache_ttl_seconds
        self.tenant_claim = tenant_claim
        self.roles_claim = roles_claim

        # JWKS configuration
        self._jwks_uri = jwks_uri
        self._jwks_cache: dict[str, Any] | None = None
        self._jwks_cached_at: datetime | None = None

        # HTTP client
        self._http_client = httpx.AsyncClient(timeout=10.0)

        logger.info(
            "OIDCProvider initialized: issuer=%s, client_id=%s",
            self.issuer,
            self.client_id,
        )

    @property
    def provider_name(self) -> str:
        return "oidc"

    @property
    def is_secure(self) -> bool:
        return True

    async def _discover_jwks_uri(self) -> str:
        """Discover JWKS URI from OpenID configuration."""
        if self._jwks_uri:
            return self._jwks_uri

        config_url = f"{self.issuer}/.well-known/openid-configuration"

        try:
            response = await self._http_client.get(config_url)
            response.raise_for_status()
            config = response.json()
            self._jwks_uri = config["jwks_uri"]
            logger.info("Discovered JWKS URI: %s", self._jwks_uri)
            return self._jwks_uri
        except Exception as e:
            logger.error("Failed to discover JWKS URI: %s", e)
            raise AuthenticationError(
                f"Failed to discover OIDC configuration: {e}",
                code="oidc_discovery_failed"
            )

    async def _get_jwks(self) -> dict[str, Any]:
        """Get JWKS with caching."""
        now = datetime.utcnow()

        # Check cache
        if (
            self._jwks_cache
            and self._jwks_cached_at
            and (now - self._jwks_cached_at).total_seconds() < self.cache_ttl
        ):
            return self._jwks_cache

        # Fetch fresh JWKS
        jwks_uri = await self._discover_jwks_uri()

        try:
            response = await self._http_client.get(jwks_uri)
            response.raise_for_status()
            self._jwks_cache = response.json()
            self._jwks_cached_at = now
            logger.debug("Refreshed JWKS cache")
            return self._jwks_cache
        except Exception as e:
            logger.error("Failed to fetch JWKS: %s", e)
            raise AuthenticationError(
                f"Failed to fetch JWKS: {e}",
                code="jwks_fetch_failed"
            )

    async def authenticate(self, request: Any) -> AuthenticatedUser:
        """Authenticate request using Bearer token."""
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization", "")

        if not auth_header:
            raise MissingTokenError()

        if not auth_header.startswith("Bearer "):
            raise InvalidTokenError("Invalid Authorization header format")

        token = auth_header[7:]  # Remove "Bearer " prefix

        if not token:
            raise MissingTokenError()

        # Validate token and get claims
        claims = await self.validate_token(token)

        # Create authenticated user
        return AuthenticatedUser.from_claims(claims, self.provider_name)

    async def validate_token(self, token: str) -> TokenClaims:
        """Validate JWT token and extract claims."""
        try:
            import jwt
            from jwt import PyJWKClient
        except ImportError:
            raise AuthenticationError(
                "PyJWT not installed. Run: pip install PyJWT[crypto]",
                code="missing_dependency"
            )

        # Get JWKS
        jwks = await self._get_jwks()

        try:
            # Decode header to get key ID
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")

            if not kid:
                raise InvalidTokenError("Token missing key ID (kid)")

            # Find the key
            key = None
            for jwk in jwks.get("keys", []):
                if jwk.get("kid") == kid:
                    key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
                    break

            if not key:
                # Key not found - might need to refresh JWKS
                self._jwks_cache = None
                jwks = await self._get_jwks()
                for jwk in jwks.get("keys", []):
                    if jwk.get("kid") == kid:
                        key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
                        break

            if not key:
                raise InvalidTokenError(f"Key ID '{kid}' not found in JWKS")

            # Verify and decode token
            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                issuer=self.issuer,
                audience=self.audience,
                leeway=self.clock_skew,
            )

            # Extract claims
            return TokenClaims(
                sub=payload.get("sub", ""),
                iss=payload.get("iss", ""),
                aud=payload.get("aud", ""),
                exp=payload.get("exp", 0),
                iat=payload.get("iat", 0),
                nbf=payload.get("nbf"),
                jti=payload.get("jti"),
                tenant_id=payload.get(self.tenant_claim, ""),
                roles=payload.get(self.roles_claim, []),
                groups=payload.get("groups", []),
                department=payload.get("department"),
                email=payload.get("email") or payload.get("preferred_username"),
                name=payload.get("name"),
                extra={
                    k: v for k, v in payload.items()
                    if k not in {
                        "sub", "iss", "aud", "exp", "iat", "nbf", "jti",
                        self.tenant_claim, self.roles_claim, "groups",
                        "department", "email", "preferred_username", "name"
                    }
                },
            )

        except jwt.ExpiredSignatureError:
            raise TokenExpiredError()
        except jwt.InvalidIssuerError:
            raise InvalidTokenError("Invalid token issuer")
        except jwt.InvalidAudienceError:
            raise InvalidTokenError("Invalid token audience")
        except jwt.InvalidSignatureError:
            raise InvalidTokenError("Invalid token signature")
        except jwt.DecodeError as e:
            raise InvalidTokenError(f"Failed to decode token: {e}")
        except Exception as e:
            logger.exception("Token validation failed")
            raise InvalidTokenError(f"Token validation failed: {e}")

    def get_login_url(self, state: str | None = None) -> str:
        """Get the OIDC authorization URL."""
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "scope": "openid profile email",
            "redirect_uri": "",  # Must be set by caller
        }
        if state:
            params["state"] = state

        # Build URL
        auth_endpoint = f"{self.issuer}/authorize"
        query = "&".join(f"{k}={v}" for k, v in params.items() if v)
        return f"{auth_endpoint}?{query}"

    async def close(self):
        """Close HTTP client."""
        await self._http_client.aclose()


class AzureADProvider(OIDCProvider):
    """Azure AD-specific OIDC provider.

    Handles Azure AD-specific claim mappings and multi-tenant scenarios.
    """

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        **kwargs,
    ):
        """Initialize Azure AD provider.

        Args:
            tenant_id: Azure AD tenant ID (or "common" for multi-tenant)
            client_id: Azure AD application (client) ID
        """
        issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"

        super().__init__(
            issuer=issuer,
            client_id=client_id,
            tenant_claim="tid",  # Azure uses "tid" for tenant ID
            roles_claim="roles",
            **kwargs,
        )

        self.azure_tenant_id = tenant_id

    @property
    def provider_name(self) -> str:
        return "azure_ad"


class OktaProvider(OIDCProvider):
    """Okta-specific OIDC provider."""

    def __init__(
        self,
        okta_domain: str,
        client_id: str,
        **kwargs,
    ):
        """Initialize Okta provider.

        Args:
            okta_domain: Okta domain (e.g., "dev-123456.okta.com")
            client_id: Okta application client ID
        """
        issuer = f"https://{okta_domain}/oauth2/default"

        super().__init__(
            issuer=issuer,
            client_id=client_id,
            tenant_claim="org_id",
            **kwargs,
        )

    @property
    def provider_name(self) -> str:
        return "okta"

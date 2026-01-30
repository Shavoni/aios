"""FastAPI authentication middleware.

Integrates authentication into the request lifecycle,
injecting verified user context into request.state.
"""

import logging
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from packages.auth.models import (
    AuthenticatedUser,
    AuthenticationError,
    MissingTokenError,
    TokenExpiredError,
)
from packages.auth.providers.base import AuthProvider

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for authentication.

    Validates authentication on all requests and injects
    AuthenticatedUser into request.state.user.

    Usage:
        from packages.auth import AuthMiddleware, get_auth_provider

        provider = get_auth_provider(config)
        app.add_middleware(AuthMiddleware, provider=provider)

    Then in endpoints:
        @app.get("/protected")
        async def protected(request: Request):
            user = request.state.user  # AuthenticatedUser
    """

    def __init__(
        self,
        app,
        provider: AuthProvider,
        exclude_paths: list[str] | None = None,
        exclude_prefixes: list[str] | None = None,
    ):
        """Initialize auth middleware.

        Args:
            app: FastAPI application
            provider: Authentication provider to use
            exclude_paths: Exact paths to skip auth (e.g., ["/health"])
            exclude_prefixes: Path prefixes to skip (e.g., ["/public/"])
        """
        super().__init__(app)
        self.provider = provider
        self.exclude_paths = set(exclude_paths or [])
        self.exclude_prefixes = tuple(exclude_prefixes or [])

        # Always exclude health check
        self.exclude_paths.add("/health")
        self.exclude_paths.add("/")

        logger.info(
            "AuthMiddleware initialized with provider: %s (secure: %s)",
            provider.provider_name,
            provider.is_secure
        )

    def should_skip_auth(self, path: str) -> bool:
        """Check if path should skip authentication."""
        # Exact match
        if path in self.exclude_paths:
            return True

        # Prefix match
        if path.startswith(self.exclude_prefixes):
            return True

        return False

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Process request through authentication."""
        path = request.url.path

        # Skip auth for excluded paths
        if self.should_skip_auth(path):
            return await call_next(request)

        try:
            # Authenticate request
            user = await self.provider.authenticate(request)

            # Inject user into request state
            request.state.user = user

            # Add user context to logging
            logger.debug(
                "Authenticated request: user=%s tenant=%s path=%s",
                user.user_id,
                user.tenant_id,
                path
            )

            # Continue to endpoint
            response = await call_next(request)

            # Add auth headers to response
            response.headers["X-Auth-Provider"] = self.provider.provider_name
            response.headers["X-Auth-User"] = user.user_id

            return response

        except MissingTokenError:
            logger.warning("Missing authentication token for path: %s", path)
            return JSONResponse(
                status_code=401,
                content={
                    "error": "authentication_required",
                    "message": "No authentication credentials provided",
                    "code": "missing_token"
                },
                headers={"WWW-Authenticate": "Bearer"}
            )

        except TokenExpiredError:
            logger.warning("Expired token for path: %s", path)
            return JSONResponse(
                status_code=401,
                content={
                    "error": "token_expired",
                    "message": "Authentication token has expired",
                    "code": "token_expired"
                },
                headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""}
            )

        except AuthenticationError as e:
            logger.warning(
                "Authentication failed for path %s: %s",
                path, e.message
            )
            return JSONResponse(
                status_code=401,
                content={
                    "error": "authentication_failed",
                    "message": e.message,
                    "code": e.code
                },
                headers={"WWW-Authenticate": "Bearer"}
            )

        except Exception as e:
            logger.exception("Unexpected auth error for path %s", path)
            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_error",
                    "message": "Authentication system error",
                    "code": "auth_internal_error"
                }
            )


def get_current_user(request: Request) -> AuthenticatedUser:
    """FastAPI dependency to get current authenticated user.

    Usage:
        from packages.auth.middleware import get_current_user

        @app.get("/me")
        async def get_me(user: AuthenticatedUser = Depends(get_current_user)):
            return {"user_id": user.user_id}
    """
    user = getattr(request.state, "user", None)
    if user is None:
        raise AuthenticationError(
            "No authenticated user in request context",
            code="no_user_context"
        )
    return user


def require_role(role: str):
    """FastAPI dependency to require a specific role.

    Usage:
        @app.get("/admin")
        async def admin_only(user: AuthenticatedUser = Depends(require_role("admin"))):
            return {"message": "Welcome admin"}
    """
    def dependency(request: Request) -> AuthenticatedUser:
        user = get_current_user(request)
        if not user.has_role(role) and role not in user.roles:
            raise AuthenticationError(
                f"Role '{role}' required",
                code="insufficient_role"
            )
        return user
    return dependency


def require_any_role(roles: list[str]):
    """FastAPI dependency to require any of the specified roles.

    Usage:
        @app.get("/staff")
        async def staff_only(
            user: AuthenticatedUser = Depends(require_any_role(["admin", "manager"]))
        ):
            return {"message": "Welcome staff"}
    """
    def dependency(request: Request) -> AuthenticatedUser:
        user = get_current_user(request)
        if not any(r in user.roles for r in roles):
            raise AuthenticationError(
                f"One of roles {roles} required",
                code="insufficient_role"
            )
        return user
    return dependency

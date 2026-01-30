"""Authorization engine.

Combines RBAC and ABAC for flexible access control.
"""

import logging
from typing import Any

from packages.auth.models import AuthenticatedUser
from packages.authz.models import (
    Permission,
    Role,
    PolicyEffect,
    ABACPolicy,
    AuthzDecision,
    SYSTEM_ROLES,
)

logger = logging.getLogger(__name__)


class AuthzEngine:
    """Authorization engine combining RBAC and ABAC.

    Evaluation order:
    1. Check explicit DENY policies (ABAC)
    2. Check RBAC roles
    3. Check ALLOW policies (ABAC)
    4. Default deny

    Usage:
        engine = AuthzEngine()
        engine.add_role(custom_role)
        engine.add_policy(custom_policy)

        decision = engine.check(user, Permission.AGENT_QUERY, resource_context)
        if decision.allowed:
            # Proceed
        else:
            # Reject with decision.reason
    """

    def __init__(self):
        """Initialize authorization engine."""
        self.roles: dict[str, Role] = dict(SYSTEM_ROLES)
        self.policies: list[ABACPolicy] = []
        self._user_roles: dict[str, list[str]] = {}  # user_id -> role_ids

        logger.info("AuthzEngine initialized with %d system roles", len(self.roles))

    def add_role(self, role: Role) -> None:
        """Add or update a role."""
        self.roles[role.role_id] = role
        logger.debug("Added role: %s", role.role_id)

    def remove_role(self, role_id: str) -> bool:
        """Remove a role."""
        if role_id in SYSTEM_ROLES:
            logger.warning("Cannot remove system role: %s", role_id)
            return False
        if role_id in self.roles:
            del self.roles[role_id]
            return True
        return False

    def add_policy(self, policy: ABACPolicy) -> None:
        """Add an ABAC policy."""
        self.policies.append(policy)
        # Keep policies sorted by priority (descending)
        self.policies.sort(key=lambda p: p.priority, reverse=True)
        logger.debug("Added policy: %s (priority %d)", policy.policy_id, policy.priority)

    def remove_policy(self, policy_id: str) -> bool:
        """Remove an ABAC policy."""
        for i, policy in enumerate(self.policies):
            if policy.policy_id == policy_id:
                self.policies.pop(i)
                return True
        return False

    def assign_role(self, user_id: str, role_id: str) -> bool:
        """Assign a role to a user."""
        if role_id not in self.roles:
            return False

        if user_id not in self._user_roles:
            self._user_roles[user_id] = []

        if role_id not in self._user_roles[user_id]:
            self._user_roles[user_id].append(role_id)

        return True

    def revoke_role(self, user_id: str, role_id: str) -> bool:
        """Revoke a role from a user."""
        if user_id in self._user_roles and role_id in self._user_roles[user_id]:
            self._user_roles[user_id].remove(role_id)
            return True
        return False

    def get_user_roles(self, user: AuthenticatedUser) -> list[Role]:
        """Get all roles for a user.

        Combines:
        - Roles from user's token claims
        - Roles assigned via assign_role()
        """
        role_ids = set(user.roles)

        # Add any additionally assigned roles
        if user.user_id in self._user_roles:
            role_ids.update(self._user_roles[user.user_id])

        # Resolve role objects
        roles = []
        for role_id in role_ids:
            if role_id in self.roles:
                roles.append(self.roles[role_id])

        return sorted(roles, key=lambda r: r.priority, reverse=True)

    def get_user_permissions(self, user: AuthenticatedUser) -> set[Permission]:
        """Get all permissions for a user (from all roles)."""
        permissions = set()
        for role in self.get_user_roles(user):
            permissions.update(role.permissions)
        return permissions

    def check(
        self,
        user: AuthenticatedUser,
        permission: Permission,
        resource: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> AuthzDecision:
        """Check if user has permission.

        Args:
            user: Authenticated user
            permission: Permission to check
            resource: Optional resource context (owner, classification, etc.)
            context: Optional additional context (time, IP, etc.)

        Returns:
            AuthzDecision with result and explanation
        """
        # Build evaluation context
        eval_context = {
            "user": {
                "id": user.user_id,
                "tenant_id": user.tenant_id,
                "email": user.email,
                "department": user.department,
                "roles": user.roles,
                "groups": user.groups,
            },
            "resource": resource or {},
            "context": context or {},
        }

        policies_evaluated = 0

        # Step 1: Check DENY policies first
        for policy in self.policies:
            if policy.effect == PolicyEffect.DENY:
                # Filter by tenant
                if policy.tenant_id and policy.tenant_id != user.tenant_id:
                    continue

                policies_evaluated += 1
                result = policy.evaluate(permission, eval_context)

                if result == PolicyEffect.DENY:
                    logger.info(
                        "Access DENIED by policy %s: user=%s permission=%s",
                        policy.policy_id, user.user_id, permission.value
                    )
                    return AuthzDecision(
                        allowed=False,
                        permission=permission,
                        reason=f"Denied by policy: {policy.name}",
                        matched_policy=policy.policy_id,
                        evaluated_policies=policies_evaluated,
                    )

        # Step 2: Check RBAC roles
        user_roles = self.get_user_roles(user)
        for role in user_roles:
            if role.has_permission(permission):
                logger.debug(
                    "Access ALLOWED by role %s: user=%s permission=%s",
                    role.role_id, user.user_id, permission.value
                )
                return AuthzDecision(
                    allowed=True,
                    permission=permission,
                    reason=f"Granted by role: {role.name}",
                    matched_role=role.role_id,
                    evaluated_policies=policies_evaluated,
                )

        # Step 3: Check ALLOW policies
        for policy in self.policies:
            if policy.effect == PolicyEffect.ALLOW:
                # Filter by tenant
                if policy.tenant_id and policy.tenant_id != user.tenant_id:
                    continue

                policies_evaluated += 1
                result = policy.evaluate(permission, eval_context)

                if result == PolicyEffect.ALLOW:
                    logger.debug(
                        "Access ALLOWED by policy %s: user=%s permission=%s",
                        policy.policy_id, user.user_id, permission.value
                    )
                    return AuthzDecision(
                        allowed=True,
                        permission=permission,
                        reason=f"Granted by policy: {policy.name}",
                        matched_policy=policy.policy_id,
                        evaluated_policies=policies_evaluated,
                    )

        # Step 4: Default deny
        logger.info(
            "Access DENIED (default): user=%s permission=%s",
            user.user_id, permission.value
        )
        return AuthzDecision(
            allowed=False,
            permission=permission,
            reason="No role or policy grants this permission",
            evaluated_policies=policies_evaluated,
        )

    def check_any(
        self,
        user: AuthenticatedUser,
        permissions: list[Permission],
        resource: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> AuthzDecision:
        """Check if user has any of the permissions."""
        for permission in permissions:
            decision = self.check(user, permission, resource, context)
            if decision.allowed:
                return decision

        return AuthzDecision(
            allowed=False,
            permission=permissions[0] if permissions else Permission.AGENT_READ,
            reason=f"None of the required permissions granted: {[p.value for p in permissions]}",
        )

    def check_all(
        self,
        user: AuthenticatedUser,
        permissions: list[Permission],
        resource: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> AuthzDecision:
        """Check if user has all of the permissions."""
        for permission in permissions:
            decision = self.check(user, permission, resource, context)
            if not decision.allowed:
                return decision

        return AuthzDecision(
            allowed=True,
            permission=permissions[0] if permissions else Permission.AGENT_READ,
            reason="All required permissions granted",
        )


# Singleton instance
_authz_engine: AuthzEngine | None = None


def get_authz_engine() -> AuthzEngine:
    """Get the authorization engine singleton."""
    global _authz_engine
    if _authz_engine is None:
        _authz_engine = AuthzEngine()
    return _authz_engine


# FastAPI dependency helpers
def require_permission(permission: Permission):
    """FastAPI dependency to require a permission.

    Usage:
        @app.get("/agents")
        async def list_agents(
            user: AuthenticatedUser = Depends(get_current_user),
            _: AuthzDecision = Depends(require_permission(Permission.AGENT_READ))
        ):
            pass
    """
    from fastapi import Depends, HTTPException, status
    from packages.auth.middleware import get_current_user

    def check(user: AuthenticatedUser = Depends(get_current_user)) -> AuthzDecision:
        engine = get_authz_engine()
        decision = engine.check(user, permission)

        if not decision.allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "forbidden",
                    "message": decision.reason,
                    "permission": permission.value,
                }
            )

        return decision

    return check


def require_any_permission(permissions: list[Permission]):
    """FastAPI dependency to require any of the permissions."""
    from fastapi import Depends, HTTPException, status
    from packages.auth.middleware import get_current_user

    def check(user: AuthenticatedUser = Depends(get_current_user)) -> AuthzDecision:
        engine = get_authz_engine()
        decision = engine.check_any(user, permissions)

        if not decision.allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "forbidden",
                    "message": decision.reason,
                    "permissions": [p.value for p in permissions],
                }
            )

        return decision

    return check

"""HAAIS AIOS Authorization Package.

Role-Based (RBAC) and Attribute-Based (ABAC) Access Control
for enterprise governance.

Usage:
    from packages.authz import AuthzEngine, Permission, check_permission

    engine = get_authz_engine()

    # Check permission
    if engine.check(user, Permission.AGENT_QUERY, resource):
        # Allowed
        pass
"""

from packages.authz.models import (
    Permission,
    Role,
    PolicyEffect,
    ABACCondition,
    ABACPolicy,
    AuthzDecision,
)
from packages.authz.engine import AuthzEngine, get_authz_engine

__all__ = [
    "Permission",
    "Role",
    "PolicyEffect",
    "ABACCondition",
    "ABACPolicy",
    "AuthzDecision",
    "AuthzEngine",
    "get_authz_engine",
]

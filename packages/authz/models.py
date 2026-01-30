"""Authorization data models.

Defines permissions, roles, and ABAC policies.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Permission(str, Enum):
    """Granular permissions for AIOS resources.

    Naming convention: {resource}:{action}
    """

    # Agent permissions
    AGENT_READ = "agent:read"
    AGENT_WRITE = "agent:write"
    AGENT_DELETE = "agent:delete"
    AGENT_QUERY = "agent:query"
    AGENT_ENABLE = "agent:enable"
    AGENT_DISABLE = "agent:disable"

    # Knowledge base permissions
    KB_READ = "kb:read"
    KB_WRITE = "kb:write"
    KB_DELETE = "kb:delete"
    KB_QUERY = "kb:query"

    # Governance permissions
    POLICY_READ = "policy:read"
    POLICY_WRITE = "policy:write"
    POLICY_DELETE = "policy:delete"
    POLICY_APPROVE = "policy:approve"

    # Approval permissions
    APPROVAL_READ = "approval:read"
    APPROVAL_REVIEW = "approval:review"
    APPROVAL_OVERRIDE = "approval:override"

    # Audit permissions
    AUDIT_READ = "audit:read"
    AUDIT_EXPORT = "audit:export"

    # Tenant administration
    TENANT_READ = "tenant:read"
    TENANT_WRITE = "tenant:write"
    TENANT_ADMIN = "tenant:admin"

    # System administration
    SYSTEM_CONFIG = "system:config"
    SYSTEM_ADMIN = "system:admin"


class Role(BaseModel):
    """A role with associated permissions.

    Roles provide a way to group permissions for easier management.
    Users are assigned roles, which grant them the role's permissions.
    """

    role_id: str = Field(description="Unique role identifier")
    name: str = Field(description="Human-readable role name")
    description: str = Field(default="", description="Role description")
    permissions: list[Permission] = Field(
        default_factory=list,
        description="Permissions granted by this role"
    )
    tenant_id: str | None = Field(
        default=None,
        description="Tenant this role belongs to (None for global roles)"
    )
    priority: int = Field(
        default=0,
        description="Role priority (higher = more authority)"
    )

    def has_permission(self, permission: Permission) -> bool:
        """Check if role grants a permission."""
        return permission in self.permissions


# Pre-defined system roles
SYSTEM_ROLES = {
    "admin": Role(
        role_id="admin",
        name="Administrator",
        description="Full system access",
        permissions=list(Permission),
        priority=100,
    ),
    "tenant_admin": Role(
        role_id="tenant_admin",
        name="Tenant Administrator",
        description="Full tenant access",
        permissions=[
            Permission.AGENT_READ, Permission.AGENT_WRITE, Permission.AGENT_DELETE,
            Permission.AGENT_QUERY, Permission.AGENT_ENABLE, Permission.AGENT_DISABLE,
            Permission.KB_READ, Permission.KB_WRITE, Permission.KB_DELETE, Permission.KB_QUERY,
            Permission.POLICY_READ, Permission.POLICY_WRITE, Permission.POLICY_DELETE,
            Permission.APPROVAL_READ, Permission.APPROVAL_REVIEW,
            Permission.AUDIT_READ,
            Permission.TENANT_READ, Permission.TENANT_WRITE,
        ],
        priority=80,
    ),
    "manager": Role(
        role_id="manager",
        name="Manager",
        description="Team management and approvals",
        permissions=[
            Permission.AGENT_READ, Permission.AGENT_QUERY,
            Permission.KB_READ, Permission.KB_QUERY,
            Permission.POLICY_READ,
            Permission.APPROVAL_READ, Permission.APPROVAL_REVIEW,
            Permission.AUDIT_READ,
        ],
        priority=50,
    ),
    "employee": Role(
        role_id="employee",
        name="Employee",
        description="Standard user access",
        permissions=[
            Permission.AGENT_READ, Permission.AGENT_QUERY,
            Permission.KB_READ, Permission.KB_QUERY,
        ],
        priority=10,
    ),
    "viewer": Role(
        role_id="viewer",
        name="Viewer",
        description="Read-only access",
        permissions=[
            Permission.AGENT_READ,
            Permission.KB_READ,
            Permission.POLICY_READ,
        ],
        priority=5,
    ),
}


class PolicyEffect(str, Enum):
    """Effect of an authorization policy."""

    ALLOW = "allow"
    DENY = "deny"


class ConditionOperator(str, Enum):
    """Operators for ABAC conditions."""

    EQUALS = "eq"
    NOT_EQUALS = "neq"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    GREATER_OR_EQUAL = "gte"
    LESS_OR_EQUAL = "lte"


class ABACCondition(BaseModel):
    """A condition for attribute-based access control.

    Evaluates: {attribute} {operator} {value}

    Examples:
    - user.department == "Engineering"
    - resource.classification in ["public", "internal"]
    - context.time_of_day < "18:00"
    """

    attribute: str = Field(
        description="Attribute path (e.g., 'user.department', 'resource.owner')"
    )
    operator: ConditionOperator = Field(description="Comparison operator")
    value: Any = Field(description="Value to compare against")

    def evaluate(self, context: dict[str, Any]) -> bool:
        """Evaluate the condition against a context."""
        # Navigate attribute path
        parts = self.attribute.split(".")
        current = context

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return False  # Attribute not found

            if current is None:
                return False

        # Apply operator
        if self.operator == ConditionOperator.EQUALS:
            return current == self.value
        elif self.operator == ConditionOperator.NOT_EQUALS:
            return current != self.value
        elif self.operator == ConditionOperator.IN:
            return current in self.value
        elif self.operator == ConditionOperator.NOT_IN:
            return current not in self.value
        elif self.operator == ConditionOperator.CONTAINS:
            return self.value in current
        elif self.operator == ConditionOperator.STARTS_WITH:
            return str(current).startswith(str(self.value))
        elif self.operator == ConditionOperator.ENDS_WITH:
            return str(current).endswith(str(self.value))
        elif self.operator == ConditionOperator.GREATER_THAN:
            return current > self.value
        elif self.operator == ConditionOperator.LESS_THAN:
            return current < self.value
        elif self.operator == ConditionOperator.GREATER_OR_EQUAL:
            return current >= self.value
        elif self.operator == ConditionOperator.LESS_OR_EQUAL:
            return current <= self.value

        return False


class ABACPolicy(BaseModel):
    """Attribute-based access control policy.

    Combines conditions with an effect (allow/deny) and target permissions.
    """

    policy_id: str = Field(description="Unique policy identifier")
    name: str = Field(description="Human-readable policy name")
    description: str = Field(default="", description="Policy description")
    effect: PolicyEffect = Field(description="Allow or deny")
    conditions: list[ABACCondition] = Field(
        default_factory=list,
        description="All conditions must match (AND logic)"
    )
    permissions: list[Permission] = Field(
        description="Permissions this policy applies to"
    )
    priority: int = Field(
        default=0,
        description="Policy priority (higher = evaluated first)"
    )
    tenant_id: str | None = Field(
        default=None,
        description="Tenant this policy belongs to"
    )

    def evaluate(self, permission: Permission, context: dict[str, Any]) -> PolicyEffect | None:
        """Evaluate policy against context.

        Returns:
            PolicyEffect if policy applies, None otherwise
        """
        # Check if policy applies to this permission
        if permission not in self.permissions:
            return None

        # Evaluate all conditions (AND logic)
        for condition in self.conditions:
            if not condition.evaluate(context):
                return None

        return self.effect


class AuthzDecision(BaseModel):
    """Result of an authorization decision."""

    allowed: bool = Field(description="Whether access is allowed")
    permission: Permission = Field(description="Permission that was checked")
    reason: str = Field(default="", description="Explanation of decision")
    matched_role: str | None = Field(
        default=None,
        description="Role that granted permission (if allowed via RBAC)"
    )
    matched_policy: str | None = Field(
        default=None,
        description="Policy that matched (if ABAC was used)"
    )
    evaluated_policies: int = Field(
        default=0,
        description="Number of policies evaluated"
    )

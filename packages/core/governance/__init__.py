"""Governance module for policy evaluation."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from packages.core.schemas.models import (
    GovernanceDecision,
    HITLMode,
    Intent,
    ProviderConstraints,
    RiskSignals,
    UserContext,
)


class ConditionOperator(str, Enum):
    """Operators for rule conditions."""

    EQUALS = "eq"
    NOT_EQUALS = "neq"
    CONTAINS = "contains"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"


class RuleCondition(BaseModel):
    """A condition that must be met for a rule to apply."""

    field: str = Field(description="Field to evaluate")
    operator: ConditionOperator = Field(default=ConditionOperator.EQUALS)
    value: Any = Field(description="Value to compare against")


class RuleAction(BaseModel):
    """Action to take when a rule matches."""

    hitl_mode: HITLMode | None = Field(default=None)
    local_only: bool = Field(default=False)
    tools_allowed: bool = Field(default=True)
    approval_required: bool = Field(default=False)
    escalation_reason: str | None = Field(default=None)


class PolicyRule(BaseModel):
    """A single policy rule."""

    id: str = Field(description="Unique rule ID")
    name: str = Field(description="Human-readable name")
    description: str = Field(default="")
    conditions: list[RuleCondition] = Field(default_factory=list)
    action: RuleAction = Field(default_factory=RuleAction)
    priority: int = Field(default=0, description="Higher = more important")


class OrganizationRules(BaseModel):
    """Organization-level rules."""

    default: list[PolicyRule] = Field(default_factory=list)


class DepartmentRules(BaseModel):
    """Department-level rules."""

    defaults: list[PolicyRule] = Field(default_factory=list)


class PolicySet(BaseModel):
    """Complete set of governance policies."""

    constitutional_rules: list[PolicyRule] = Field(default_factory=list)
    organization_rules: OrganizationRules = Field(default_factory=OrganizationRules)
    department_rules: dict[str, DepartmentRules] = Field(default_factory=dict)


HITL_PRIORITY = {
    HITLMode.INFORM: 0,
    HITLMode.DRAFT: 1,
    HITLMode.ESCALATE: 2,
}


def _evaluate_condition(
    condition: RuleCondition,
    intent: Intent,
    risk: RiskSignals,
    ctx: UserContext,
) -> bool:
    """Evaluate a single condition."""
    field_parts = condition.field.split(".")

    if field_parts[0] == "risk" and field_parts[1] == "contains":
        return risk.contains(str(condition.value))

    if field_parts[0] == "intent":
        field_name = field_parts[1]
        actual_value: Any = getattr(intent, field_name, None)
    elif field_parts[0] == "ctx":
        field_name = field_parts[1]
        actual_value = getattr(ctx, field_name, None)
    else:
        return False

    if condition.operator == ConditionOperator.EQUALS:
        return bool(actual_value == condition.value)
    elif condition.operator == ConditionOperator.NOT_EQUALS:
        return bool(actual_value != condition.value)
    elif condition.operator == ConditionOperator.CONTAINS:
        return condition.value in str(actual_value)

    return False


def _evaluate_rule(
    rule: PolicyRule,
    intent: Intent,
    risk: RiskSignals,
    ctx: UserContext,
) -> bool:
    """Check if all conditions of a rule are met."""
    if not rule.conditions:
        return False

    return all(
        _evaluate_condition(cond, intent, risk, ctx)
        for cond in rule.conditions
    )


def _merge_action(decision: GovernanceDecision, action: RuleAction, rule_id: str) -> None:
    """Merge a rule action into the decision."""
    decision.policy_trigger_ids.append(rule_id)

    if action.hitl_mode:
        current_priority = HITL_PRIORITY.get(decision.hitl_mode, 0)
        new_priority = HITL_PRIORITY.get(action.hitl_mode, 0)
        if new_priority > current_priority:
            decision.hitl_mode = action.hitl_mode

    if action.local_only:
        decision.provider_constraints.local_only = True

    if not action.tools_allowed:
        decision.tools_allowed = False

    if action.approval_required:
        decision.approval_required = True

    if action.escalation_reason and not decision.escalation_reason:
        decision.escalation_reason = action.escalation_reason


def evaluate_governance(
    intent: Intent,
    risk: RiskSignals,
    ctx: UserContext,
    policy_set: PolicySet,
) -> GovernanceDecision:
    """Evaluate governance policies and return decision."""
    decision = GovernanceDecision(
        hitl_mode=HITLMode.INFORM,
        tools_allowed=True,
        approval_required=False,
        provider_constraints=ProviderConstraints(),
    )

    matching_rules: list[tuple[int, PolicyRule]] = []

    for rule in policy_set.constitutional_rules:
        if _evaluate_rule(rule, intent, risk, ctx):
            matching_rules.append((rule.priority + 10000, rule))

    for rule in policy_set.organization_rules.default:
        if _evaluate_rule(rule, intent, risk, ctx):
            matching_rules.append((rule.priority + 5000, rule))

    dept_rules = policy_set.department_rules.get(intent.domain)
    if dept_rules:
        for rule in dept_rules.defaults:
            if _evaluate_rule(rule, intent, risk, ctx):
                matching_rules.append((rule.priority, rule))

    matching_rules.sort(key=lambda x: x[0], reverse=True)

    for _, rule in matching_rules:
        _merge_action(decision, rule.action, rule.id)

    return decision


class PolicyLoader:
    """Load policies from various sources."""

    def load_from_dict(self, raw: dict[str, Any]) -> PolicySet:
        """Load policies from a dictionary."""
        if not raw:
            return PolicySet()

        constitutional = []
        for rule_data in raw.get("constitutional_rules", []):
            constitutional.append(self._parse_rule(rule_data))

        org_default = []
        org_rules_data = raw.get("organization_rules", {})
        for rule_data in org_rules_data.get("default", []):
            org_default.append(self._parse_rule(rule_data))

        dept_rules: dict[str, DepartmentRules] = {}
        for dept_name, dept_data in raw.get("department_rules", {}).items():
            dept_defaults = []
            for rule_data in dept_data.get("defaults", []):
                dept_defaults.append(self._parse_rule(rule_data))
            dept_rules[dept_name] = DepartmentRules(defaults=dept_defaults)

        return PolicySet(
            constitutional_rules=constitutional,
            organization_rules=OrganizationRules(default=org_default),
            department_rules=dept_rules,
        )

    def _parse_rule(self, data: dict[str, Any]) -> PolicyRule:
        """Parse a single rule from dict."""
        conditions = []
        for cond_data in data.get("conditions", []):
            conditions.append(RuleCondition(
                field=cond_data["field"],
                operator=ConditionOperator(cond_data.get("operator", "eq")),
                value=cond_data["value"],
            ))

        action_data = data.get("action", {})
        hitl_mode = None
        if "hitl_mode" in action_data:
            hitl_mode = HITLMode(action_data["hitl_mode"])

        action = RuleAction(
            hitl_mode=hitl_mode,
            local_only=action_data.get("local_only", False),
            tools_allowed=action_data.get("tools_allowed", True),
            approval_required=action_data.get("approval_required", False),
            escalation_reason=action_data.get("escalation_reason"),
        )

        return PolicyRule(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            conditions=conditions,
            action=action,
            priority=data.get("priority", 0),
        )


__all__ = [
    "ConditionOperator",
    "DepartmentRules",
    "OrganizationRules",
    "PolicyLoader",
    "PolicyRule",
    "PolicySet",
    "RuleAction",
    "RuleCondition",
    "evaluate_governance",
]

# Import manager for convenience access
from packages.core.governance.manager import (
    GovernanceManager,
    get_governance_manager,
)

__all__ += [
    "GovernanceManager",
    "get_governance_manager",
]

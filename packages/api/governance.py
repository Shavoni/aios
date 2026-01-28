"""Governance management API endpoints.

Provides centralized control over HAAIS governance policies that apply
across all deployed agents. Changes here propagate immediately.

Scopes:
- Global: Applies to ALL agents
- Domain: Applies to all agents in a domain
- Agent: Applies to a specific agent only
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from packages.core.governance.manager import get_governance_manager
from packages.core.governance import (
    PolicyRule,
    RuleAction,
    RuleCondition,
    ConditionOperator,
)
from packages.core.schemas.models import HITLMode

router = APIRouter(prefix="/governance", tags=["Governance"])


# =============================================================================
# Request/Response Models
# =============================================================================


class ProhibitedTopicRequest(BaseModel):
    """Request to add a prohibited topic."""

    topic: str = Field(..., min_length=1, description="Topic to prohibit")
    scope: str = Field(
        default="global",
        description="Scope: 'global', 'domain:<name>', or 'agent:<id>'",
    )


class ProhibitedTopicResponse(BaseModel):
    """Response for prohibited topic operations."""

    topic: str
    scope: str
    active: bool = True


class ProhibitedTopicsListResponse(BaseModel):
    """List of all prohibited topics."""

    global_topics: list[str]
    domain_topics: dict[str, list[str]]
    agent_topics: dict[str, list[str]]


class PolicyRuleRequest(BaseModel):
    """Request to create a policy rule."""

    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    description: str = ""
    tier: str = Field(
        default="organization",
        description="Tier: 'constitutional', 'organization', or 'department:<name>'",
    )
    conditions: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of conditions: {field, operator, value}",
    )
    hitl_mode: str | None = Field(default=None, description="INFORM, DRAFT, or ESCALATE")
    local_only: bool = False
    tools_allowed: bool = True
    approval_required: bool = False
    escalation_reason: str | None = None
    priority: int = 0


class PolicyRuleResponse(BaseModel):
    """Response for policy rule operations."""

    id: str
    name: str
    tier: str
    active: bool = True


class AllRulesResponse(BaseModel):
    """Response containing all governance rules."""

    constitutional: list[dict[str, Any]]
    organization: list[dict[str, Any]]
    department: dict[str, list[dict[str, Any]]]
    prohibited_topics: ProhibitedTopicsListResponse


class GovernanceTestRequest(BaseModel):
    """Request to test governance evaluation."""

    query: str = Field(..., min_length=1)
    agent_id: str | None = None
    domain: str = "General"


class GovernanceTestResponse(BaseModel):
    """Response from governance test."""

    hitl_mode: str
    tools_allowed: bool
    approval_required: bool
    escalation_reason: str | None
    policy_trigger_ids: list[str]
    would_escalate: bool
    would_draft: bool


# =============================================================================
# Prohibited Topics Endpoints
# =============================================================================


@router.post("/prohibited-topics", response_model=ProhibitedTopicResponse)
async def add_prohibited_topic(request: ProhibitedTopicRequest) -> ProhibitedTopicResponse:
    """Add a prohibited topic.

    Scope options:
    - "global": Blocks topic across ALL agents
    - "domain:Public Health": Blocks topic for all agents in Public Health domain
    - "agent:public-health": Blocks topic for the specific public-health agent only

    Example: To block all Park Authority questions everywhere:
    POST /governance/prohibited-topics
    {"topic": "Park Authority", "scope": "global"}
    """
    governance = get_governance_manager()

    if request.scope == "global":
        governance.add_prohibited_topic(request.topic)
    elif request.scope.startswith("domain:"):
        domain = request.scope.split(":", 1)[1]
        governance.add_domain_prohibition(domain, request.topic)
    elif request.scope.startswith("agent:"):
        agent_id = request.scope.split(":", 1)[1]
        governance.add_agent_prohibition(agent_id, request.topic)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scope: {request.scope}. Use 'global', 'domain:<name>', or 'agent:<id>'",
        )

    return ProhibitedTopicResponse(topic=request.topic, scope=request.scope)


@router.delete("/prohibited-topics")
async def remove_prohibited_topic(request: ProhibitedTopicRequest) -> dict[str, bool]:
    """Remove a prohibited topic.

    Uses the same scope format as adding.
    """
    governance = get_governance_manager()
    removed = False

    if request.scope == "global":
        removed = governance.remove_prohibited_topic(request.topic)
    elif request.scope.startswith("domain:"):
        domain = request.scope.split(":", 1)[1]
        removed = governance.remove_domain_prohibition(domain, request.topic)
    elif request.scope.startswith("agent:"):
        agent_id = request.scope.split(":", 1)[1]
        removed = governance.remove_agent_prohibition(agent_id, request.topic)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scope: {request.scope}",
        )

    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Topic '{request.topic}' not found in scope '{request.scope}'",
        )

    return {"removed": True}


@router.get("/prohibited-topics", response_model=ProhibitedTopicsListResponse)
async def list_prohibited_topics() -> ProhibitedTopicsListResponse:
    """List all prohibited topics organized by scope."""
    governance = get_governance_manager()
    all_topics = governance.list_prohibited_topics()

    global_topics: list[str] = []
    domain_topics: dict[str, list[str]] = {}
    agent_topics: dict[str, list[str]] = {}

    for topic in all_topics:
        if topic.startswith("domain:"):
            # Format: domain:<domain>:<topic>
            parts = topic.split(":", 2)
            if len(parts) == 3:
                domain = parts[1]
                actual_topic = parts[2]
                if domain not in domain_topics:
                    domain_topics[domain] = []
                domain_topics[domain].append(actual_topic)
        elif topic.startswith("agent:"):
            # Format: agent:<agent_id>:<topic>
            parts = topic.split(":", 2)
            if len(parts) == 3:
                agent_id = parts[1]
                actual_topic = parts[2]
                if agent_id not in agent_topics:
                    agent_topics[agent_id] = []
                agent_topics[agent_id].append(actual_topic)
        else:
            global_topics.append(topic)

    return ProhibitedTopicsListResponse(
        global_topics=global_topics,
        domain_topics=domain_topics,
        agent_topics=agent_topics,
    )


# =============================================================================
# Policy Rules Endpoints
# =============================================================================


@router.post("/rules", response_model=PolicyRuleResponse)
async def add_policy_rule(request: PolicyRuleRequest) -> PolicyRuleResponse:
    """Add a new governance policy rule.

    Tiers (priority order):
    - constitutional: Highest priority, core organizational principles
    - organization: Organization-wide policies
    - department:<name>: Department-specific policies

    Conditions evaluate against:
    - intent.domain, intent.task, intent.audience, intent.impact
    - risk.contains (check for risk signals: PII, FINANCIAL, LEGAL, PERSONNEL)
    - ctx.role, ctx.department

    Example - Require approval for high-impact financial requests:
    {
        "id": "fin-001",
        "name": "High-Impact Financial Approval",
        "tier": "organization",
        "conditions": [
            {"field": "risk.contains", "operator": "eq", "value": "FINANCIAL"},
            {"field": "intent.impact", "operator": "eq", "value": "high"}
        ],
        "hitl_mode": "DRAFT",
        "approval_required": true
    }
    """
    governance = get_governance_manager()

    # Build conditions
    conditions = []
    for cond in request.conditions:
        conditions.append(RuleCondition(
            field=cond["field"],
            operator=ConditionOperator(cond.get("operator", "eq")),
            value=cond["value"],
        ))

    # Build action
    hitl_mode = None
    if request.hitl_mode:
        hitl_mode = HITLMode(request.hitl_mode)

    action = RuleAction(
        hitl_mode=hitl_mode,
        local_only=request.local_only,
        tools_allowed=request.tools_allowed,
        approval_required=request.approval_required,
        escalation_reason=request.escalation_reason,
    )

    rule = PolicyRule(
        id=request.id,
        name=request.name,
        description=request.description,
        conditions=conditions,
        action=action,
        priority=request.priority,
    )

    # Add to appropriate tier
    if request.tier == "constitutional":
        governance.add_constitutional_rule(rule)
    elif request.tier == "organization":
        governance.add_organization_rule(rule)
    elif request.tier.startswith("department:"):
        department = request.tier.split(":", 1)[1]
        governance.add_department_rule(department, rule)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier: {request.tier}",
        )

    return PolicyRuleResponse(id=request.id, name=request.name, tier=request.tier)


@router.delete("/rules/{rule_id}")
async def remove_policy_rule(rule_id: str) -> dict[str, bool]:
    """Remove a policy rule by ID."""
    governance = get_governance_manager()
    removed = governance.remove_rule(rule_id)

    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule '{rule_id}' not found",
        )

    return {"removed": True}


@router.get("/rules", response_model=AllRulesResponse)
async def list_all_rules() -> AllRulesResponse:
    """List all governance rules and prohibited topics."""
    governance = get_governance_manager()
    rules = governance.get_all_rules()
    topics_response = await list_prohibited_topics()

    def serialize_rule(rule: PolicyRule) -> dict[str, Any]:
        return {
            "id": rule.id,
            "name": rule.name,
            "description": rule.description,
            "priority": rule.priority,
            "hitl_mode": rule.action.hitl_mode.value if rule.action.hitl_mode else None,
            "conditions": [
                {"field": c.field, "operator": c.operator.value, "value": c.value}
                for c in rule.conditions
            ],
        }

    dept_rules = {}
    if isinstance(rules.get("department"), dict):
        for dept, dept_rule_list in rules["department"].items():
            dept_rules[dept] = [serialize_rule(r) for r in dept_rule_list]

    return AllRulesResponse(
        constitutional=[serialize_rule(r) for r in rules.get("constitutional", [])],
        organization=[serialize_rule(r) for r in rules.get("organization", [])],
        department=dept_rules,
        prohibited_topics=topics_response,
    )


# =============================================================================
# Governance Testing Endpoint
# =============================================================================


@router.post("/test", response_model=GovernanceTestResponse)
async def test_governance(request: GovernanceTestRequest) -> GovernanceTestResponse:
    """Test how governance would evaluate a query.

    Use this to preview what would happen before deploying new rules.
    Does NOT actually process the query - just evaluates governance.
    """
    governance = get_governance_manager()

    if request.agent_id:
        decision = governance.evaluate_for_agent(
            query=request.query,
            agent_id=request.agent_id,
            domain=request.domain,
        )
    else:
        decision = governance.evaluate(
            query=request.query,
            domain=request.domain,
        )

    return GovernanceTestResponse(
        hitl_mode=decision.hitl_mode.value,
        tools_allowed=decision.tools_allowed,
        approval_required=decision.approval_required,
        escalation_reason=decision.escalation_reason,
        policy_trigger_ids=decision.policy_trigger_ids,
        would_escalate=decision.hitl_mode == HITLMode.ESCALATE,
        would_draft=decision.hitl_mode == HITLMode.DRAFT,
    )


# =============================================================================
# Reload Endpoint
# =============================================================================


@router.post("/reload")
async def reload_policies() -> dict[str, str]:
    """Reload governance policies from disk.

    Useful if policies were edited directly in the JSON file.
    """
    governance = get_governance_manager()
    governance.reload_policies()
    return {"status": "reloaded"}

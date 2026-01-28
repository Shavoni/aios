"""Governance Manager for centralized policy control.

This module provides a singleton governance manager that:
- Loads and stores policies centrally
- Enables runtime policy updates that propagate to all agents
- Persists policies to disk for durability
- Provides quick intent/risk classification for governance evaluation
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from packages.core.governance import (
    PolicyLoader,
    PolicyRule,
    PolicySet,
    RuleAction,
    RuleCondition,
    ConditionOperator,
    evaluate_governance,
)
from packages.core.schemas.models import (
    GovernanceDecision,
    HITLMode,
    Intent,
    RiskSignals,
    UserContext,
)

# Default policy file location
DEFAULT_POLICY_PATH = Path("data/governance_policies.json")

# Risk signal patterns
RISK_PATTERNS: dict[str, list[str]] = {
    "PII": [
        r"\b(ssn|social security)\b",
        r"\b(credit card|ccn)\b",
        r"\b(password|credential)\b",
        r"\bconfidential\b",
    ],
    "FINANCIAL": [
        r"\b(salary|compensation|pay)\b",
        r"\b(budget|funding)\b",
        r"\b(contract|procurement)\b",
    ],
    "LEGAL": [
        r"\b(lawsuit|litigation)\b",
        r"\b(attorney|lawyer)\b",
        r"\b(legal advice)\b",
    ],
    "PERSONNEL": [
        r"\b(fire|terminate|disciplin)\b",
        r"\b(performance review)\b",
        r"\b(employee complaint)\b",
    ],
}


class GovernanceManager:
    """Centralized governance policy manager.

    Provides runtime policy management that propagates to all agents.
    When you update a policy here, all agent queries will immediately
    enforce the new rules.
    """

    _instance: GovernanceManager | None = None

    def __init__(self, policy_path: Path | None = None):
        self._policy_path = policy_path or DEFAULT_POLICY_PATH
        self._policy_set = PolicySet()
        self._loader = PolicyLoader()
        self._prohibited_topics: list[str] = []
        self._load_policies()

    @classmethod
    def get_instance(cls) -> GovernanceManager:
        """Get the singleton governance manager."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton (for testing)."""
        cls._instance = None

    def _load_policies(self) -> None:
        """Load policies from disk."""
        if self._policy_path.exists():
            try:
                raw = json.loads(self._policy_path.read_text(encoding="utf-8"))
                self._policy_set = self._loader.load_from_dict(raw)
                self._prohibited_topics = raw.get("prohibited_topics", [])
            except Exception:
                self._policy_set = PolicySet()
                self._prohibited_topics = []
        else:
            self._init_default_policies()

    def _save_policies(self) -> None:
        """Persist policies to disk."""
        self._policy_path.parent.mkdir(parents=True, exist_ok=True)

        data = self._serialize_policy_set()
        data["prohibited_topics"] = self._prohibited_topics

        self._policy_path.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8",
        )

    def _serialize_policy_set(self) -> dict[str, Any]:
        """Serialize policy set to dict for storage."""
        def serialize_rule(rule: PolicyRule) -> dict[str, Any]:
            conditions = []
            for cond in rule.conditions:
                conditions.append({
                    "field": cond.field,
                    "operator": cond.operator.value,
                    "value": cond.value,
                })

            action: dict[str, Any] = {}
            if rule.action.hitl_mode:
                action["hitl_mode"] = rule.action.hitl_mode.value
            if rule.action.local_only:
                action["local_only"] = True
            if not rule.action.tools_allowed:
                action["tools_allowed"] = False
            if rule.action.approval_required:
                action["approval_required"] = True
            if rule.action.escalation_reason:
                action["escalation_reason"] = rule.action.escalation_reason

            return {
                "id": rule.id,
                "name": rule.name,
                "description": rule.description,
                "conditions": conditions,
                "action": action,
                "priority": rule.priority,
            }

        return {
            "constitutional_rules": [
                serialize_rule(r) for r in self._policy_set.constitutional_rules
            ],
            "organization_rules": {
                "default": [
                    serialize_rule(r) for r in self._policy_set.organization_rules.default
                ],
            },
            "department_rules": {
                dept: {"defaults": [serialize_rule(r) for r in rules.defaults]}
                for dept, rules in self._policy_set.department_rules.items()
            },
        }

    def _init_default_policies(self) -> None:
        """Initialize with HAAIS-compliant default policies."""
        from packages.core.governance import (
            OrganizationRules,
            DepartmentRules,
        )

        # Constitutional rules (Tier 1 - highest priority)
        constitutional = [
            PolicyRule(
                id="const-001",
                name="PII Protection",
                description="Escalate requests involving personally identifiable information",
                conditions=[
                    RuleCondition(field="risk.contains", operator=ConditionOperator.EQUALS, value="PII"),
                ],
                action=RuleAction(
                    hitl_mode=HITLMode.ESCALATE,
                    escalation_reason="Request involves personally identifiable information",
                ),
                priority=100,
            ),
            PolicyRule(
                id="const-002",
                name="Legal Matters",
                description="Escalate legal questions requiring attorney review",
                conditions=[
                    RuleCondition(field="risk.contains", operator=ConditionOperator.EQUALS, value="LEGAL"),
                ],
                action=RuleAction(
                    hitl_mode=HITLMode.DRAFT,
                    escalation_reason="Legal matters require human review",
                ),
                priority=90,
            ),
            PolicyRule(
                id="const-003",
                name="High Impact Actions",
                description="Require approval for high-impact decisions",
                conditions=[
                    RuleCondition(field="intent.impact", operator=ConditionOperator.EQUALS, value="high"),
                ],
                action=RuleAction(
                    hitl_mode=HITLMode.DRAFT,
                    approval_required=True,
                ),
                priority=80,
            ),
        ]

        # Organization-wide rules (Tier 2)
        org_rules = [
            PolicyRule(
                id="org-001",
                name="Financial Sensitivity",
                description="Draft mode for financial information",
                conditions=[
                    RuleCondition(field="risk.contains", operator=ConditionOperator.EQUALS, value="FINANCIAL"),
                ],
                action=RuleAction(hitl_mode=HITLMode.DRAFT),
                priority=50,
            ),
            PolicyRule(
                id="org-002",
                name="Personnel Matters",
                description="Draft mode for HR/personnel topics",
                conditions=[
                    RuleCondition(field="risk.contains", operator=ConditionOperator.EQUALS, value="PERSONNEL"),
                ],
                action=RuleAction(hitl_mode=HITLMode.DRAFT),
                priority=50,
            ),
        ]

        self._policy_set = PolicySet(
            constitutional_rules=constitutional,
            organization_rules=OrganizationRules(default=org_rules),
            department_rules={},
        )

        self._save_policies()

    # =========================================================================
    # Policy Query & Evaluation
    # =========================================================================

    def get_policy_set(self) -> PolicySet:
        """Get the current policy set."""
        return self._policy_set

    def classify_intent(self, query: str, domain: str = "General") -> Intent:
        """Quick intent classification from query text.

        For more sophisticated classification, this should integrate
        with the LLM router. This provides basic keyword-based classification.
        """
        query_lower = query.lower()

        # Determine impact level
        impact = "low"
        high_impact_keywords = ["delete", "remove", "terminate", "approve", "authorize", "grant"]
        medium_impact_keywords = ["update", "change", "modify", "submit", "create"]

        for kw in high_impact_keywords:
            if kw in query_lower:
                impact = "high"
                break
        else:
            for kw in medium_impact_keywords:
                if kw in query_lower:
                    impact = "medium"
                    break

        # Determine audience
        audience = "internal"
        if any(kw in query_lower for kw in ["public", "citizen", "resident", "community"]):
            audience = "external"

        # Determine task type
        task = "inquiry"
        if any(kw in query_lower for kw in ["how", "what", "when", "where", "why"]):
            task = "inquiry"
        elif any(kw in query_lower for kw in ["create", "add", "new"]):
            task = "create"
        elif any(kw in query_lower for kw in ["update", "change", "modify"]):
            task = "update"
        elif any(kw in query_lower for kw in ["delete", "remove"]):
            task = "delete"

        return Intent(
            domain=domain,
            task=task,
            audience=audience,
            impact=impact,
            confidence=0.8,
        )

    def detect_risk_signals(self, query: str) -> RiskSignals:
        """Detect risk signals in the query text."""
        signals: list[str] = []
        query_lower = query.lower()

        for signal_type, patterns in RISK_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    if signal_type not in signals:
                        signals.append(signal_type)
                    break

        # Check prohibited topics
        for topic in self._prohibited_topics:
            if topic.lower() in query_lower:
                signals.append(f"PROHIBITED_TOPIC:{topic}")

        return RiskSignals(signals=signals)

    def evaluate(
        self,
        query: str,
        domain: str = "General",
        user_context: UserContext | None = None,
    ) -> GovernanceDecision:
        """Evaluate governance for a query.

        This is the main entry point for governance evaluation.
        Returns a GovernanceDecision indicating how the request should be handled.
        """
        intent = self.classify_intent(query, domain)
        risk = self.detect_risk_signals(query)

        if user_context is None:
            user_context = UserContext(tenant_id="default")

        # Check for prohibited topics first
        for signal in risk.signals:
            if signal.startswith("PROHIBITED_TOPIC:"):
                topic = signal.split(":", 1)[1]
                return GovernanceDecision(
                    hitl_mode=HITLMode.ESCALATE,
                    tools_allowed=False,
                    approval_required=True,
                    escalation_reason=f"Query involves prohibited topic: {topic}",
                    policy_trigger_ids=["prohibited-topic"],
                )

        return evaluate_governance(intent, risk, user_context, self._policy_set)

    # =========================================================================
    # Policy Management API
    # =========================================================================

    def add_prohibited_topic(self, topic: str) -> None:
        """Add a topic that should be blocked across all agents.

        Example: add_prohibited_topic("Park Authority") will cause all
        agents to escalate/block questions about Park Authority.
        """
        if topic not in self._prohibited_topics:
            self._prohibited_topics.append(topic)
            self._save_policies()

    def remove_prohibited_topic(self, topic: str) -> bool:
        """Remove a prohibited topic."""
        if topic in self._prohibited_topics:
            self._prohibited_topics.remove(topic)
            self._save_policies()
            return True
        return False

    def list_prohibited_topics(self) -> list[str]:
        """List all prohibited topics."""
        return list(self._prohibited_topics)

    # =========================================================================
    # Agent-Specific Governance
    # =========================================================================

    def add_agent_prohibition(self, agent_id: str, topic: str) -> None:
        """Prohibit a topic for a specific agent only.

        Example: add_agent_prohibition("public-health", "vaccines")
        """
        key = f"agent:{agent_id}:{topic}"
        if key not in self._prohibited_topics:
            self._prohibited_topics.append(key)
            self._save_policies()

    def remove_agent_prohibition(self, agent_id: str, topic: str) -> bool:
        """Remove a topic prohibition from a specific agent."""
        key = f"agent:{agent_id}:{topic}"
        if key in self._prohibited_topics:
            self._prohibited_topics.remove(key)
            self._save_policies()
            return True
        return False

    def get_agent_prohibitions(self, agent_id: str) -> list[str]:
        """Get all prohibited topics for a specific agent."""
        prefix = f"agent:{agent_id}:"
        return [
            topic.replace(prefix, "")
            for topic in self._prohibited_topics
            if topic.startswith(prefix)
        ]

    def add_domain_prohibition(self, domain: str, topic: str) -> None:
        """Prohibit a topic for all agents in a domain.

        Example: add_domain_prohibition("Public Health", "alternative medicine")
        """
        key = f"domain:{domain}:{topic}"
        if key not in self._prohibited_topics:
            self._prohibited_topics.append(key)
            self._save_policies()

    def remove_domain_prohibition(self, domain: str, topic: str) -> bool:
        """Remove a topic prohibition from a domain."""
        key = f"domain:{domain}:{topic}"
        if key in self._prohibited_topics:
            self._prohibited_topics.remove(key)
            self._save_policies()
            return True
        return False

    def get_domain_prohibitions(self, domain: str) -> list[str]:
        """Get all prohibited topics for a domain."""
        prefix = f"domain:{domain}:"
        return [
            topic.replace(prefix, "")
            for topic in self._prohibited_topics
            if topic.startswith(prefix)
        ]

    def _topic_matches(self, topic: str, query: str) -> bool:
        """Check if a topic matches within the query.

        Uses fuzzy matching to handle:
        - Singular/plural variations (vaccine/vaccines)
        - Word boundaries
        - Case insensitivity
        """
        topic_lower = topic.lower().strip()
        query_lower = query.lower()

        # Direct substring match
        if topic_lower in query_lower:
            return True

        # Handle singular/plural - check if topic stem matches
        # Remove common suffixes for matching
        topic_stem = topic_lower.rstrip('s').rstrip('es').rstrip('ies') + 'y' if topic_lower.endswith('ies') else topic_lower.rstrip('s')

        # Build pattern with word boundary awareness
        words = query_lower.split()
        for word in words:
            word_clean = re.sub(r'[^\w]', '', word)  # Remove punctuation
            word_stem = word_clean.rstrip('s')

            # Check if stems match
            if topic_stem == word_stem or topic_lower == word_clean:
                return True

            # Check if topic is contained in word or vice versa
            if len(topic_stem) >= 3:
                if topic_stem in word_clean or word_clean in topic_stem:
                    return True

        return False

    def evaluate_for_agent(
        self,
        query: str,
        agent_id: str,
        domain: str = "General",
        user_context: UserContext | None = None,
    ) -> GovernanceDecision:
        """Evaluate governance for a specific agent's query.

        Checks:
        1. Agent-specific prohibitions
        2. Domain-specific prohibitions
        3. Global prohibited topics
        4. All policy rules
        """
        intent = self.classify_intent(query, domain)
        risk = self.detect_risk_signals(query)

        if user_context is None:
            user_context = UserContext(tenant_id="default")

        # Check agent-specific prohibitions
        for topic in self.get_agent_prohibitions(agent_id):
            if self._topic_matches(topic, query):
                return GovernanceDecision(
                    hitl_mode=HITLMode.ESCALATE,
                    tools_allowed=False,
                    approval_required=True,
                    escalation_reason=f"This agent cannot provide information about: {topic}",
                    policy_trigger_ids=[f"agent-prohibition:{agent_id}:{topic}"],
                )

        # Check domain-specific prohibitions
        for topic in self.get_domain_prohibitions(domain):
            if self._topic_matches(topic, query):
                return GovernanceDecision(
                    hitl_mode=HITLMode.ESCALATE,
                    tools_allowed=False,
                    approval_required=True,
                    escalation_reason=f"This domain cannot provide information about: {topic}",
                    policy_trigger_ids=[f"domain-prohibition:{domain}:{topic}"],
                )

        # Check global prohibited topics
        for signal in risk.signals:
            if signal.startswith("PROHIBITED_TOPIC:"):
                topic = signal.split(":", 1)[1]
                return GovernanceDecision(
                    hitl_mode=HITLMode.ESCALATE,
                    tools_allowed=False,
                    approval_required=True,
                    escalation_reason=f"Query involves prohibited topic: {topic}",
                    policy_trigger_ids=["prohibited-topic"],
                )

        return evaluate_governance(intent, risk, user_context, self._policy_set)

    def add_constitutional_rule(self, rule: PolicyRule) -> None:
        """Add a new constitutional (Tier 1) rule."""
        self._policy_set.constitutional_rules.append(rule)
        self._save_policies()

    def add_organization_rule(self, rule: PolicyRule) -> None:
        """Add a new organization-wide (Tier 2) rule."""
        self._policy_set.organization_rules.default.append(rule)
        self._save_policies()

    def add_department_rule(self, department: str, rule: PolicyRule) -> None:
        """Add a new department-specific (Tier 3) rule."""
        from packages.core.governance import DepartmentRules

        if department not in self._policy_set.department_rules:
            self._policy_set.department_rules[department] = DepartmentRules()

        self._policy_set.department_rules[department].defaults.append(rule)
        self._save_policies()

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID from any tier."""
        # Check constitutional
        for i, rule in enumerate(self._policy_set.constitutional_rules):
            if rule.id == rule_id:
                self._policy_set.constitutional_rules.pop(i)
                self._save_policies()
                return True

        # Check organization
        for i, rule in enumerate(self._policy_set.organization_rules.default):
            if rule.id == rule_id:
                self._policy_set.organization_rules.default.pop(i)
                self._save_policies()
                return True

        # Check departments
        for dept_rules in self._policy_set.department_rules.values():
            for i, rule in enumerate(dept_rules.defaults):
                if rule.id == rule_id:
                    dept_rules.defaults.pop(i)
                    self._save_policies()
                    return True

        return False

    def get_all_rules(self) -> dict[str, list[PolicyRule]]:
        """Get all rules organized by tier."""
        return {
            "constitutional": self._policy_set.constitutional_rules,
            "organization": self._policy_set.organization_rules.default,
            "department": {
                dept: rules.defaults
                for dept, rules in self._policy_set.department_rules.items()
            },
        }

    def reload_policies(self) -> None:
        """Reload policies from disk (useful after external edits)."""
        self._load_policies()


def get_governance_manager() -> GovernanceManager:
    """Get the singleton governance manager."""
    return GovernanceManager.get_instance()


__all__ = [
    "GovernanceManager",
    "get_governance_manager",
    "RISK_PATTERNS",
]

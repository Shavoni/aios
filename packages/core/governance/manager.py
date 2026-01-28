"""Governance Manager for centralized policy control.

This module provides a singleton governance manager that:
- Loads and stores policies centrally
- Enables runtime policy updates that propagate to all agents
- Persists policies to disk for durability
- Provides quick intent/risk classification for governance evaluation
- Tracks policy versions and change history
- Supports approval workflow for policy changes
- Detects configuration drift
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime
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
POLICY_HISTORY_PATH = Path("data/governance_history.json")
PENDING_POLICY_PATH = Path("data/pending_policy_changes.json")

# =============================================================================
# Policy Change Types and History Tracking
# =============================================================================

class PolicyChangeType:
    """Types of policy changes."""
    ADD_RULE = "add_rule"
    REMOVE_RULE = "remove_rule"
    UPDATE_RULE = "update_rule"
    ADD_PROHIBITION = "add_prohibition"
    REMOVE_PROHIBITION = "remove_prohibition"
    FULL_RELOAD = "full_reload"
    ROLLBACK = "rollback"


class PolicyChange:
    """Represents a proposed or applied policy change."""

    def __init__(
        self,
        change_id: str,
        change_type: str,
        description: str,
        proposed_by: str = "system",
        data: dict | None = None,
        status: str = "pending",  # pending, approved, rejected, applied
        created_at: str | None = None,
        reviewed_by: str | None = None,
        reviewed_at: str | None = None,
        review_notes: str | None = None,
    ):
        self.change_id = change_id
        self.change_type = change_type
        self.description = description
        self.proposed_by = proposed_by
        self.data = data or {}
        self.status = status
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.reviewed_by = reviewed_by
        self.reviewed_at = reviewed_at
        self.review_notes = review_notes

    def to_dict(self) -> dict:
        return {
            "change_id": self.change_id,
            "change_type": self.change_type,
            "description": self.description,
            "proposed_by": self.proposed_by,
            "data": self.data,
            "status": self.status,
            "created_at": self.created_at,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at,
            "review_notes": self.review_notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PolicyChange":
        return cls(
            change_id=data["change_id"],
            change_type=data["change_type"],
            description=data["description"],
            proposed_by=data.get("proposed_by", "system"),
            data=data.get("data", {}),
            status=data.get("status", "pending"),
            created_at=data.get("created_at"),
            reviewed_by=data.get("reviewed_by"),
            reviewed_at=data.get("reviewed_at"),
            review_notes=data.get("review_notes"),
        )


class PolicyVersion:
    """Represents a point-in-time snapshot of policies."""

    def __init__(
        self,
        version_id: str,
        version_number: int,
        created_at: str,
        created_by: str,
        change_description: str,
        policy_hash: str,
        policy_snapshot: dict,
    ):
        self.version_id = version_id
        self.version_number = version_number
        self.created_at = created_at
        self.created_by = created_by
        self.change_description = change_description
        self.policy_hash = policy_hash
        self.policy_snapshot = policy_snapshot

    def to_dict(self) -> dict:
        return {
            "version_id": self.version_id,
            "version_number": self.version_number,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "change_description": self.change_description,
            "policy_hash": self.policy_hash,
            "policy_snapshot": self.policy_snapshot,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PolicyVersion":
        return cls(
            version_id=data["version_id"],
            version_number=data["version_number"],
            created_at=data["created_at"],
            created_by=data["created_by"],
            change_description=data["change_description"],
            policy_hash=data["policy_hash"],
            policy_snapshot=data["policy_snapshot"],
        )


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

    Features:
    - Single source of truth for all governance policies
    - Policy versioning with full history
    - Approval workflow for policy changes
    - Drift detection
    - Override prevention with immutable rules
    """

    _instance: GovernanceManager | None = None

    def __init__(self, policy_path: Path | None = None):
        self._policy_path = policy_path or DEFAULT_POLICY_PATH
        self._history_path = POLICY_HISTORY_PATH
        self._pending_path = PENDING_POLICY_PATH
        self._policy_set = PolicySet()
        self._loader = PolicyLoader()
        self._prohibited_topics: list[str] = []
        self._immutable_rules: set[str] = set()  # Rule IDs that cannot be modified
        self._current_version: int = 0
        self._policy_hash: str = ""
        self._versions: list[PolicyVersion] = []
        self._pending_changes: list[PolicyChange] = []
        self._require_approval: bool = True  # Require approval for policy changes
        self._load_policies()
        self._load_history()
        self._load_pending_changes()

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
                self._immutable_rules = set(raw.get("immutable_rules", []))
                self._current_version = raw.get("version", 0)
                self._require_approval = raw.get("require_approval", True)
                self._policy_hash = self._compute_policy_hash()
            except Exception:
                self._policy_set = PolicySet()
                self._prohibited_topics = []
                self._immutable_rules = set()
        else:
            self._init_default_policies()

    def _load_history(self) -> None:
        """Load policy version history from disk."""
        if self._history_path.exists():
            try:
                data = json.loads(self._history_path.read_text(encoding="utf-8"))
                self._versions = [PolicyVersion.from_dict(v) for v in data.get("versions", [])]
            except Exception:
                self._versions = []
        else:
            self._versions = []

    def _save_history(self) -> None:
        """Save policy version history to disk."""
        self._history_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"versions": [v.to_dict() for v in self._versions]}
        self._history_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load_pending_changes(self) -> None:
        """Load pending policy changes from disk."""
        if self._pending_path.exists():
            try:
                data = json.loads(self._pending_path.read_text(encoding="utf-8"))
                self._pending_changes = [PolicyChange.from_dict(c) for c in data.get("pending", [])]
            except Exception:
                self._pending_changes = []
        else:
            self._pending_changes = []

    def _save_pending_changes(self) -> None:
        """Save pending policy changes to disk."""
        self._pending_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"pending": [c.to_dict() for c in self._pending_changes]}
        self._pending_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _compute_policy_hash(self) -> str:
        """Compute a hash of the current policy state for drift detection."""
        policy_data = self._serialize_policy_set()
        policy_data["prohibited_topics"] = sorted(self._prohibited_topics)
        policy_str = json.dumps(policy_data, sort_keys=True)
        return hashlib.sha256(policy_str.encode()).hexdigest()[:16]

    def _create_version_snapshot(self, description: str, created_by: str = "system") -> PolicyVersion:
        """Create a version snapshot of current policies."""
        self._current_version += 1
        version = PolicyVersion(
            version_id=str(uuid.uuid4()),
            version_number=self._current_version,
            created_at=datetime.utcnow().isoformat(),
            created_by=created_by,
            change_description=description,
            policy_hash=self._compute_policy_hash(),
            policy_snapshot=self._serialize_policy_set(),
        )
        version.policy_snapshot["prohibited_topics"] = list(self._prohibited_topics)
        version.policy_snapshot["immutable_rules"] = list(self._immutable_rules)
        self._versions.append(version)
        self._save_history()
        return version

    def _save_policies(self, description: str = "Policy update", changed_by: str = "system") -> None:
        """Persist policies to disk with versioning."""
        self._policy_path.parent.mkdir(parents=True, exist_ok=True)

        # Create version snapshot before saving
        self._create_version_snapshot(description, changed_by)

        data = self._serialize_policy_set()
        data["prohibited_topics"] = self._prohibited_topics
        data["immutable_rules"] = list(self._immutable_rules)
        data["version"] = self._current_version
        data["require_approval"] = self._require_approval
        data["last_modified"] = datetime.utcnow().isoformat()
        data["last_modified_by"] = changed_by

        self._policy_path.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8",
        )
        self._policy_hash = self._compute_policy_hash()

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

        self._save_policies("Initial default policies", "system")

    # =========================================================================
    # B) Override Prevention - Immutable Rules
    # =========================================================================

    def mark_rule_immutable(self, rule_id: str) -> bool:
        """Mark a rule as immutable (cannot be modified or deleted)."""
        # Check if rule exists
        all_rules = self.get_all_rules()
        found = False
        for rules in [all_rules["constitutional"], all_rules["organization"]]:
            if any(r.id == rule_id for r in rules):
                found = True
                break
        if not found:
            for dept_rules in all_rules.get("department", {}).values():
                if any(r.id == rule_id for r in dept_rules):
                    found = True
                    break

        if not found:
            return False

        self._immutable_rules.add(rule_id)
        self._save_policies(f"Marked rule {rule_id} as immutable", "system")
        return True

    def unmark_rule_immutable(
        self,
        rule_id: str,
        override_key: str,
        admin_user: str = "admin",
    ) -> bool:
        """Unmark a rule as immutable (requires valid override key).

        ENTERPRISE SECURITY: This is a privileged operation that requires:
        1. Valid override_key matching GOVERNANCE_OVERRIDE_KEY environment variable
        2. Rule must currently be marked as immutable
        3. Action is logged with admin user for audit trail

        Args:
            rule_id: The rule ID to unmark
            override_key: Must match GOVERNANCE_OVERRIDE_KEY env var
            admin_user: Admin performing this action (for audit)

        Returns:
            True if successfully unmarked, False if rule wasn't immutable

        Raises:
            PermissionError: If override_key is invalid or missing
        """
        import os

        # SECURITY: Validate override key against environment variable
        expected_key = os.environ.get("GOVERNANCE_OVERRIDE_KEY", "")

        if not expected_key:
            raise PermissionError(
                "GOVERNANCE_OVERRIDE_KEY environment variable not set. "
                "Cannot unmark immutable rules without system configuration."
            )

        if not override_key or override_key != expected_key:
            raise PermissionError(
                f"Invalid override key provided by '{admin_user}'. "
                "Cannot unmark immutable rule without valid authorization."
            )

        if rule_id not in self._immutable_rules:
            return False

        self._immutable_rules.remove(rule_id)
        self._save_policies(
            f"PRIVILEGED: Unmarked rule {rule_id} as immutable by {admin_user}",
            admin_user,
        )
        return True

    def is_rule_immutable(self, rule_id: str) -> bool:
        """Check if a rule is immutable."""
        return rule_id in self._immutable_rules

    def get_immutable_rules(self) -> list[str]:
        """Get list of immutable rule IDs."""
        return list(self._immutable_rules)

    def check_override_conflict(self, new_rule: PolicyRule) -> dict | None:
        """Check if a new rule would conflict with higher-priority rules.

        Returns conflict details or None if no conflict.
        """
        for const_rule in self._policy_set.constitutional_rules:
            if const_rule.priority > new_rule.priority:
                # Check for overlapping conditions
                for new_cond in new_rule.conditions:
                    for const_cond in const_rule.conditions:
                        if new_cond.field == const_cond.field:
                            return {
                                "conflict_type": "priority_override",
                                "conflicting_rule_id": const_rule.id,
                                "conflicting_rule_name": const_rule.name,
                                "conflicting_priority": const_rule.priority,
                                "new_rule_priority": new_rule.priority,
                                "field": new_cond.field,
                                "warning": f"Rule '{new_rule.name}' may be overridden by higher-priority rule '{const_rule.name}'",
                            }
        return None

    # =========================================================================
    # C) Policy Versioning
    # =========================================================================

    def get_current_version(self) -> int:
        """Get the current policy version number."""
        return self._current_version

    def get_version_history(self, limit: int = 50) -> list[dict]:
        """Get policy version history."""
        versions = sorted(self._versions, key=lambda v: v.version_number, reverse=True)[:limit]
        return [v.to_dict() for v in versions]

    def get_version(self, version_id: str) -> PolicyVersion | None:
        """Get a specific version by ID."""
        for v in self._versions:
            if v.version_id == version_id:
                return v
        return None

    def get_version_by_number(self, version_number: int) -> PolicyVersion | None:
        """Get a specific version by version number."""
        for v in self._versions:
            if v.version_number == version_number:
                return v
        return None

    def rollback_to_version(self, version_id: str, rolled_back_by: str = "admin") -> bool:
        """Rollback policies to a previous version."""
        version = self.get_version(version_id)
        if not version:
            return False

        # Load the snapshot
        snapshot = version.policy_snapshot
        self._policy_set = self._loader.load_from_dict(snapshot)
        self._prohibited_topics = snapshot.get("prohibited_topics", [])
        self._immutable_rules = set(snapshot.get("immutable_rules", []))

        # Save with new version (rollback creates a new version)
        self._save_policies(
            f"Rollback to version {version.version_number} ({version.change_description})",
            rolled_back_by
        )
        return True

    def compare_versions(self, version_id_1: str, version_id_2: str) -> dict:
        """Compare two policy versions."""
        v1 = self.get_version(version_id_1)
        v2 = self.get_version(version_id_2)

        if not v1 or not v2:
            return {"error": "One or both versions not found"}

        # Compare snapshots
        diff = {
            "version_1": {"id": v1.version_id, "number": v1.version_number},
            "version_2": {"id": v2.version_id, "number": v2.version_number},
            "changes": [],
        }

        # Compare constitutional rules
        v1_const_ids = {r["id"] for r in v1.policy_snapshot.get("constitutional_rules", [])}
        v2_const_ids = {r["id"] for r in v2.policy_snapshot.get("constitutional_rules", [])}

        for rule_id in v2_const_ids - v1_const_ids:
            diff["changes"].append({"type": "added", "tier": "constitutional", "rule_id": rule_id})
        for rule_id in v1_const_ids - v2_const_ids:
            diff["changes"].append({"type": "removed", "tier": "constitutional", "rule_id": rule_id})

        # Compare prohibited topics
        v1_topics = set(v1.policy_snapshot.get("prohibited_topics", []))
        v2_topics = set(v2.policy_snapshot.get("prohibited_topics", []))

        for topic in v2_topics - v1_topics:
            diff["changes"].append({"type": "added", "tier": "prohibited_topic", "topic": topic})
        for topic in v1_topics - v2_topics:
            diff["changes"].append({"type": "removed", "tier": "prohibited_topic", "topic": topic})

        return diff

    # =========================================================================
    # D) Approval Workflow for Policy Changes
    # =========================================================================

    def set_require_approval(self, require: bool) -> None:
        """Enable or disable approval requirement for policy changes."""
        self._require_approval = require
        self._save_policies(
            f"{'Enabled' if require else 'Disabled'} approval requirement",
            "admin"
        )

    def is_approval_required(self) -> bool:
        """Check if approval is required for policy changes."""
        return self._require_approval

    def propose_rule_change(
        self,
        change_type: str,
        description: str,
        data: dict,
        proposed_by: str = "system",
    ) -> PolicyChange:
        """Propose a policy change that requires approval."""
        change = PolicyChange(
            change_id=str(uuid.uuid4()),
            change_type=change_type,
            description=description,
            proposed_by=proposed_by,
            data=data,
            status="pending",
        )
        self._pending_changes.append(change)
        self._save_pending_changes()
        return change

    def get_pending_changes(self) -> list[dict]:
        """Get all pending policy changes."""
        return [c.to_dict() for c in self._pending_changes if c.status == "pending"]

    def get_change(self, change_id: str) -> PolicyChange | None:
        """Get a specific change by ID."""
        for c in self._pending_changes:
            if c.change_id == change_id:
                return c
        return None

    def approve_change(
        self,
        change_id: str,
        reviewed_by: str,
        review_notes: str = "",
    ) -> dict:
        """Approve and apply a pending policy change."""
        change = self.get_change(change_id)
        if not change:
            return {"success": False, "error": "Change not found"}

        if change.status != "pending":
            return {"success": False, "error": f"Change is not pending (status: {change.status})"}

        # Apply the change based on type
        try:
            if change.change_type == PolicyChangeType.ADD_RULE:
                self._apply_add_rule(change.data, reviewed_by)
            elif change.change_type == PolicyChangeType.REMOVE_RULE:
                self._apply_remove_rule(change.data, reviewed_by)
            elif change.change_type == PolicyChangeType.ADD_PROHIBITION:
                self._apply_add_prohibition(change.data, reviewed_by)
            elif change.change_type == PolicyChangeType.REMOVE_PROHIBITION:
                self._apply_remove_prohibition(change.data, reviewed_by)
            else:
                return {"success": False, "error": f"Unknown change type: {change.change_type}"}

            # Update change status
            change.status = "applied"
            change.reviewed_by = reviewed_by
            change.reviewed_at = datetime.utcnow().isoformat()
            change.review_notes = review_notes
            self._save_pending_changes()

            return {"success": True, "message": f"Change {change_id} approved and applied"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def reject_change(
        self,
        change_id: str,
        reviewed_by: str,
        review_notes: str = "",
    ) -> dict:
        """Reject a pending policy change."""
        change = self.get_change(change_id)
        if not change:
            return {"success": False, "error": "Change not found"}

        if change.status != "pending":
            return {"success": False, "error": f"Change is not pending (status: {change.status})"}

        change.status = "rejected"
        change.reviewed_by = reviewed_by
        change.reviewed_at = datetime.utcnow().isoformat()
        change.review_notes = review_notes
        self._save_pending_changes()

        return {"success": True, "message": f"Change {change_id} rejected"}

    def _apply_add_rule(self, data: dict, applied_by: str) -> None:
        """Apply an add rule change."""
        tier = data.get("tier", "organization")
        rule_data = data.get("rule", {})

        rule = PolicyRule(
            id=rule_data.get("id", str(uuid.uuid4())),
            name=rule_data.get("name", "Unnamed Rule"),
            description=rule_data.get("description", ""),
            conditions=[
                RuleCondition(
                    field=c["field"],
                    operator=ConditionOperator(c["operator"]),
                    value=c["value"],
                )
                for c in rule_data.get("conditions", [])
            ],
            action=RuleAction(
                hitl_mode=HITLMode(rule_data.get("action", {}).get("hitl_mode", "INFORM")),
                approval_required=rule_data.get("action", {}).get("approval_required", False),
                escalation_reason=rule_data.get("action", {}).get("escalation_reason"),
            ),
            priority=rule_data.get("priority", 50),
        )

        if tier == "constitutional":
            self.add_constitutional_rule(rule)
        elif tier == "organization":
            self.add_organization_rule(rule)
        else:
            self.add_department_rule(tier, rule)

    def _apply_remove_rule(self, data: dict, applied_by: str) -> None:
        """Apply a remove rule change."""
        rule_id = data.get("rule_id")
        if rule_id:
            if self.is_rule_immutable(rule_id):
                raise ValueError(f"Cannot remove immutable rule: {rule_id}")
            self.remove_rule(rule_id)

    def _apply_add_prohibition(self, data: dict, applied_by: str) -> None:
        """Apply an add prohibition change."""
        topic = data.get("topic")
        scope = data.get("scope", "global")
        scope_id = data.get("scope_id")

        if scope == "global":
            self.add_prohibited_topic(topic)
        elif scope == "agent":
            self.add_agent_prohibition(scope_id, topic)
        elif scope == "domain":
            self.add_domain_prohibition(scope_id, topic)

    def _apply_remove_prohibition(self, data: dict, applied_by: str) -> None:
        """Apply a remove prohibition change."""
        topic = data.get("topic")
        scope = data.get("scope", "global")
        scope_id = data.get("scope_id")

        if scope == "global":
            self.remove_prohibited_topic(topic)
        elif scope == "agent":
            self.remove_agent_prohibition(scope_id, topic)
        elif scope == "domain":
            self.remove_domain_prohibition(scope_id, topic)

    # =========================================================================
    # E) Drift Detection
    # =========================================================================

    def get_policy_hash(self) -> str:
        """Get the current policy hash for drift detection."""
        return self._policy_hash

    def check_drift(self) -> dict:
        """Check if policies have drifted from the stored hash.

        Returns drift status and details.
        """
        current_hash = self._compute_policy_hash()
        stored_hash = self._policy_hash

        if current_hash == stored_hash:
            return {
                "drift_detected": False,
                "status": "ok",
                "current_hash": current_hash,
                "message": "No drift detected",
            }

        return {
            "drift_detected": True,
            "status": "warning",
            "stored_hash": stored_hash,
            "current_hash": current_hash,
            "message": "Policy drift detected! In-memory policies differ from stored hash.",
        }

    def check_file_drift(self) -> dict:
        """Check if the policy file has been modified externally."""
        if not self._policy_path.exists():
            return {
                "drift_detected": True,
                "status": "error",
                "message": "Policy file not found!",
            }

        # Load file and compute hash
        try:
            raw = json.loads(self._policy_path.read_text(encoding="utf-8"))
            file_policy_set = self._loader.load_from_dict(raw)
            file_prohibited = raw.get("prohibited_topics", [])

            # Compute hash of file contents
            file_data = {
                "constitutional_rules": [{"id": r.id} for r in file_policy_set.constitutional_rules],
                "organization_rules": {"default": [{"id": r.id} for r in file_policy_set.organization_rules.default]},
                "prohibited_topics": sorted(file_prohibited),
            }
            file_str = json.dumps(file_data, sort_keys=True)
            file_hash = hashlib.sha256(file_str.encode()).hexdigest()[:16]

            # Compute hash of in-memory contents
            mem_data = {
                "constitutional_rules": [{"id": r.id} for r in self._policy_set.constitutional_rules],
                "organization_rules": {"default": [{"id": r.id} for r in self._policy_set.organization_rules.default]},
                "prohibited_topics": sorted(self._prohibited_topics),
            }
            mem_str = json.dumps(mem_data, sort_keys=True)
            mem_hash = hashlib.sha256(mem_str.encode()).hexdigest()[:16]

            if file_hash == mem_hash:
                return {
                    "drift_detected": False,
                    "status": "ok",
                    "message": "File and memory are in sync",
                }

            return {
                "drift_detected": True,
                "status": "warning",
                "file_hash": file_hash,
                "memory_hash": mem_hash,
                "message": "Policy file differs from in-memory policies. External modification detected.",
            }

        except Exception as e:
            return {
                "drift_detected": True,
                "status": "error",
                "message": f"Error checking file drift: {str(e)}",
            }

    def sync_from_file(self) -> dict:
        """Reload policies from file to resolve drift."""
        try:
            old_hash = self._policy_hash
            self._load_policies()
            new_hash = self._compute_policy_hash()

            return {
                "success": True,
                "old_hash": old_hash,
                "new_hash": new_hash,
                "message": "Policies reloaded from file",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def get_drift_report(self) -> dict:
        """Get a comprehensive drift report."""
        memory_drift = self.check_drift()
        file_drift = self.check_file_drift()

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "current_version": self._current_version,
            "policy_hash": self._policy_hash,
            "memory_drift": memory_drift,
            "file_drift": file_drift,
            "overall_status": "ok" if not (memory_drift["drift_detected"] or file_drift["drift_detected"]) else "drift_detected",
        }

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
        """Add a new constitutional (Tier 1) rule.

        ENTERPRISE SECURITY: Prevents duplicate rule IDs and modification
        of immutable rules to maintain constitutional integrity.

        Raises:
            ValueError: If rule ID already exists or is immutable
        """
        # Check if rule ID is immutable
        if self.is_rule_immutable(rule.id):
            raise ValueError(
                f"Rule '{rule.id}' is marked as immutable and cannot be modified. "
                "Contact a system administrator with override authority."
            )

        # Check if rule ID already exists in constitutional rules
        existing_ids = {r.id for r in self._policy_set.constitutional_rules}
        if rule.id in existing_ids:
            raise ValueError(
                f"Constitutional rule '{rule.id}' already exists. "
                "Cannot add duplicate rules. Use update_constitutional_rule() to modify."
            )

        # Check for override conflict with higher-priority rules
        conflict = self.check_override_conflict(rule)
        if conflict:
            # Log warning but allow (lower priority won't override higher)
            pass  # In production, would log this warning

        self._policy_set.constitutional_rules.append(rule)
        self._save_policies(f"Added constitutional rule: {rule.id}", "system")

    def add_organization_rule(self, rule: PolicyRule) -> None:
        """Add a new organization-wide (Tier 2) rule.

        ENTERPRISE SECURITY: Prevents duplicate rule IDs and modification
        of immutable rules.

        Raises:
            ValueError: If rule ID already exists or is immutable
        """
        # Check if rule ID is immutable
        if self.is_rule_immutable(rule.id):
            raise ValueError(
                f"Rule '{rule.id}' is marked as immutable and cannot be modified."
            )

        # Check if rule ID already exists
        existing_ids = {r.id for r in self._policy_set.organization_rules.default}
        if rule.id in existing_ids:
            raise ValueError(
                f"Organization rule '{rule.id}' already exists. "
                "Cannot add duplicate rules."
            )

        self._policy_set.organization_rules.default.append(rule)
        self._save_policies(f"Added organization rule: {rule.id}", "system")

    def add_department_rule(self, department: str, rule: PolicyRule) -> None:
        """Add a new department-specific (Tier 3) rule.

        ENTERPRISE SECURITY: Prevents duplicate rule IDs and modification
        of immutable rules. Department rules cannot override constitutional
        rules due to priority system (+10000 boost for constitutional).

        Raises:
            ValueError: If rule ID already exists globally or is immutable
        """
        from packages.core.governance import DepartmentRules

        # SECURITY: Check if rule ID is immutable (matches any tier)
        if self.is_rule_immutable(rule.id):
            raise ValueError(
                f"Rule '{rule.id}' is marked as immutable and cannot be modified. "
                "Department rules cannot shadow immutable rules."
            )

        # SECURITY: Check if rule ID already exists in ANY tier
        all_rule_ids = self._get_all_rule_ids()
        if rule.id in all_rule_ids:
            raise ValueError(
                f"Rule ID '{rule.id}' already exists in another tier. "
                "Department rules cannot use IDs that exist in constitutional or organization rules."
            )

        # Check for duplicate within department
        if department in self._policy_set.department_rules:
            dept_rule_ids = {r.id for r in self._policy_set.department_rules[department].defaults}
            if rule.id in dept_rule_ids:
                raise ValueError(
                    f"Department rule '{rule.id}' already exists in {department}. "
                    "Cannot add duplicate rules."
                )

        if department not in self._policy_set.department_rules:
            self._policy_set.department_rules[department] = DepartmentRules()

        self._policy_set.department_rules[department].defaults.append(rule)
        self._save_policies(f"Added department rule: {rule.id} to {department}", "system")

    def _get_all_rule_ids(self) -> set[str]:
        """Get all rule IDs across all tiers.

        SECURITY: Used to prevent ID collisions across tiers.
        """
        rule_ids = set()

        # Constitutional rules
        for rule in self._policy_set.constitutional_rules:
            rule_ids.add(rule.id)

        # Organization rules
        for rule in self._policy_set.organization_rules.default:
            rule_ids.add(rule.id)

        # Department rules (all departments)
        for dept_rules in self._policy_set.department_rules.values():
            for rule in dept_rules.defaults:
                rule_ids.add(rule.id)

        return rule_ids

    def remove_rule(self, rule_id: str, force: bool = False) -> bool:
        """Remove a rule by ID from any tier.

        Args:
            rule_id: The ID of the rule to remove
            force: If True, allows removing immutable rules (use with caution)

        Returns:
            True if rule was removed, False if not found

        Raises:
            ValueError: If trying to remove an immutable rule without force=True
        """
        # Check if rule is immutable
        if self.is_rule_immutable(rule_id) and not force:
            raise ValueError(f"Cannot remove immutable rule: {rule_id}. Use force=True to override.")

        # Check constitutional
        for i, rule in enumerate(self._policy_set.constitutional_rules):
            if rule.id == rule_id:
                self._policy_set.constitutional_rules.pop(i)
                self._save_policies(f"Removed constitutional rule: {rule_id}", "admin")
                return True

        # Check organization
        for i, rule in enumerate(self._policy_set.organization_rules.default):
            if rule.id == rule_id:
                self._policy_set.organization_rules.default.pop(i)
                self._save_policies(f"Removed organization rule: {rule_id}", "admin")
                return True

        # Check departments
        for dept_rules in self._policy_set.department_rules.values():
            for i, rule in enumerate(dept_rules.defaults):
                if rule.id == rule_id:
                    dept_rules.defaults.pop(i)
                    self._save_policies(f"Removed department rule: {rule_id}", "admin")
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
    "PolicyChange",
    "PolicyChangeType",
    "PolicyVersion",
]

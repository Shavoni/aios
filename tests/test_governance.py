"""Unit tests for the Governance Kernel."""

import pytest

from packages.core.schemas.models import (
    HITLMode,
    Intent,
    RiskSignals,
    UserContext,
)
from packages.core.governance import (
    ConditionOperator,
    DepartmentRules,
    OrganizationRules,
    PolicyLoader,
    PolicyRule,
    PolicySet,
    RuleAction,
    RuleCondition,
    evaluate_governance,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def default_ctx() -> UserContext:
    """Default user context for testing."""
    return UserContext(
        tenant_id="test-tenant",
        user_id="user-123",
        role="employee",
        department="General",
    )


@pytest.fixture
def sample_policy_set() -> PolicySet:
    """Sample policy set covering key test cases."""
    return PolicySet(
        constitutional_rules=[
            # PII requires local_only
            PolicyRule(
                id="const_pii_local",
                name="PII Local Only",
                description="PII data must be processed locally",
                conditions=[
                    RuleCondition(
                        field="risk.contains",
                        operator=ConditionOperator.EQUALS,
                        value="PII",
                    )
                ],
                action=RuleAction(local_only=True),
                priority=1000,
            ),
            # Legal/contract requires ESCALATE
            PolicyRule(
                id="const_legal_escalate",
                name="Legal Escalation",
                description="Legal matters require human escalation",
                conditions=[
                    RuleCondition(
                        field="risk.contains",
                        operator=ConditionOperator.EQUALS,
                        value="LEGAL_CONTRACT",
                    )
                ],
                action=RuleAction(
                    hitl_mode=HITLMode.ESCALATE,
                    escalation_reason="Legal contract requires human review",
                ),
                priority=999,
            ),
        ],
        organization_rules=OrganizationRules(
            default=[
                # Public audience requires DRAFT
                PolicyRule(
                    id="org_public_draft",
                    name="Public Statement Draft",
                    description="Public statements require draft review",
                    conditions=[
                        RuleCondition(
                            field="intent.audience",
                            operator=ConditionOperator.EQUALS,
                            value="public",
                        )
                    ],
                    action=RuleAction(
                        hitl_mode=HITLMode.DRAFT,
                        approval_required=True,
                    ),
                    priority=500,
                ),
                # High impact requires approval
                PolicyRule(
                    id="org_high_impact",
                    name="High Impact Approval",
                    description="High impact actions require approval",
                    conditions=[
                        RuleCondition(
                            field="intent.impact",
                            operator=ConditionOperator.EQUALS,
                            value="high",
                        )
                    ],
                    action=RuleAction(
                        hitl_mode=HITLMode.DRAFT,
                        approval_required=True,
                    ),
                    priority=400,
                ),
            ]
        ),
        department_rules={
            "Comms": DepartmentRules(
                defaults=[
                    # Comms public statements get extra scrutiny
                    PolicyRule(
                        id="dept_comms_public",
                        name="Comms Public Statement",
                        description="Comms public statements require DRAFT",
                        conditions=[
                            RuleCondition(
                                field="intent.task",
                                operator=ConditionOperator.EQUALS,
                                value="draft_statement",
                            )
                        ],
                        action=RuleAction(hitl_mode=HITLMode.DRAFT),
                        priority=300,
                    ),
                ]
            ),
            "Legal": DepartmentRules(
                defaults=[
                    # Legal department escalates contract reviews
                    PolicyRule(
                        id="dept_legal_contract",
                        name="Legal Contract Review",
                        description="Legal contract reviews require escalation",
                        conditions=[
                            RuleCondition(
                                field="intent.task",
                                operator=ConditionOperator.EQUALS,
                                value="contract_review",
                            )
                        ],
                        action=RuleAction(
                            hitl_mode=HITLMode.ESCALATE,
                            escalation_reason="Contract review requires legal team",
                        ),
                        priority=300,
                    ),
                ]
            ),
        },
    )


# ============================================================================
# Test: Public Statement -> DRAFT
# ============================================================================

class TestPublicStatementDraft:
    """Test that public statements trigger DRAFT mode."""

    def test_public_audience_triggers_draft(
        self, default_ctx: UserContext, sample_policy_set: PolicySet
    ):
        """Public audience should trigger DRAFT mode."""
        intent = Intent(
            domain="Comms",
            task="draft_statement",
            audience="public",
            impact="medium",
            confidence=0.9,
        )
        risk = RiskSignals(signals=["PUBLIC_STATEMENT"])

        decision = evaluate_governance(intent, risk, default_ctx, sample_policy_set)

        assert decision.hitl_mode == HITLMode.DRAFT
        assert decision.approval_required is True
        assert "org_public_draft" in decision.policy_trigger_ids

    def test_internal_audience_defaults_inform(
        self, default_ctx: UserContext, sample_policy_set: PolicySet
    ):
        """Internal audience with no other triggers should default to INFORM."""
        intent = Intent(
            domain="General",
            task="answer_question",
            audience="internal",
            impact="low",
            confidence=0.9,
        )
        risk = RiskSignals(signals=[])

        decision = evaluate_governance(intent, risk, default_ctx, sample_policy_set)

        assert decision.hitl_mode == HITLMode.INFORM


# ============================================================================
# Test: Contract/Legal -> ESCALATE
# ============================================================================

class TestLegalEscalate:
    """Test that legal/contract matters trigger ESCALATE."""

    def test_legal_contract_risk_triggers_escalate(
        self, default_ctx: UserContext, sample_policy_set: PolicySet
    ):
        """LEGAL_CONTRACT risk signal should trigger ESCALATE."""
        intent = Intent(
            domain="Legal",
            task="contract_review",
            audience="internal",
            impact="high",
            confidence=0.8,
        )
        risk = RiskSignals(signals=["LEGAL_CONTRACT"])

        decision = evaluate_governance(intent, risk, default_ctx, sample_policy_set)

        assert decision.hitl_mode == HITLMode.ESCALATE
        assert decision.escalation_reason == "Legal contract requires human review"
        assert "const_legal_escalate" in decision.policy_trigger_ids

    def test_legal_task_without_risk_uses_department_rule(
        self, default_ctx: UserContext, sample_policy_set: PolicySet
    ):
        """Legal task without constitutional risk signal uses department rule."""
        intent = Intent(
            domain="Legal",
            task="contract_review",
            audience="internal",
            impact="medium",
            confidence=0.8,
        )
        risk = RiskSignals(signals=[])  # No LEGAL_CONTRACT signal

        decision = evaluate_governance(intent, risk, default_ctx, sample_policy_set)

        assert decision.hitl_mode == HITLMode.ESCALATE
        assert "dept_legal_contract" in decision.policy_trigger_ids


# ============================================================================
# Test: PII -> local_only = True
# ============================================================================

class TestPIILocalOnly:
    """Test that PII risk triggers local_only constraint."""

    def test_pii_risk_sets_local_only(
        self, default_ctx: UserContext, sample_policy_set: PolicySet
    ):
        """PII risk signal should set provider_constraints.local_only = True."""
        intent = Intent(
            domain="HR",
            task="lookup_employee",
            audience="internal",
            impact="medium",
            confidence=0.9,
        )
        risk = RiskSignals(signals=["PII"])

        decision = evaluate_governance(intent, risk, default_ctx, sample_policy_set)

        assert decision.provider_constraints.local_only is True
        assert "const_pii_local" in decision.policy_trigger_ids

    def test_no_pii_allows_external(
        self, default_ctx: UserContext, sample_policy_set: PolicySet
    ):
        """Without PII, local_only should be False."""
        intent = Intent(
            domain="General",
            task="answer_question",
            audience="internal",
            impact="low",
            confidence=0.9,
        )
        risk = RiskSignals(signals=[])

        decision = evaluate_governance(intent, risk, default_ctx, sample_policy_set)

        assert decision.provider_constraints.local_only is False


# ============================================================================
# Test: Default -> INFORM
# ============================================================================

class TestDefaultInform:
    """Test that default behavior is INFORM."""

    def test_no_matching_rules_defaults_inform(self, default_ctx: UserContext):
        """With no matching rules, default should be INFORM."""
        intent = Intent(
            domain="General",
            task="answer_question",
            audience="internal",
            impact="low",
            confidence=0.9,
        )
        risk = RiskSignals(signals=[])

        # Empty policy set
        policy_set = PolicySet()

        decision = evaluate_governance(intent, risk, default_ctx, policy_set)

        assert decision.hitl_mode == HITLMode.INFORM
        assert decision.tools_allowed is True
        assert decision.approval_required is False
        assert decision.escalation_reason is None
        assert decision.policy_trigger_ids == []

    def test_low_risk_internal_defaults_inform(
        self, default_ctx: UserContext, sample_policy_set: PolicySet
    ):
        """Low risk internal requests should default to INFORM."""
        intent = Intent(
            domain="General",
            task="answer_question",
            audience="internal",
            impact="low",
            confidence=0.95,
        )
        risk = RiskSignals(signals=[])

        decision = evaluate_governance(intent, risk, default_ctx, sample_policy_set)

        assert decision.hitl_mode == HITLMode.INFORM


# ============================================================================
# Test: Constitutional Rules Take Precedence
# ============================================================================

class TestConstitutionalPrecedence:
    """Test that constitutional rules take precedence over others."""

    def test_constitutional_overrides_department(
        self, default_ctx: UserContext, sample_policy_set: PolicySet
    ):
        """Constitutional rules should take precedence over department rules."""
        intent = Intent(
            domain="Legal",
            task="contract_review",
            audience="internal",
            impact="high",
            confidence=0.9,
        )
        # Both LEGAL_CONTRACT (constitutional) and dept rule should match
        risk = RiskSignals(signals=["LEGAL_CONTRACT"])

        decision = evaluate_governance(intent, risk, default_ctx, sample_policy_set)

        # Constitutional rule should be first in trigger list
        assert decision.policy_trigger_ids[0] == "const_legal_escalate"
        assert decision.escalation_reason == "Legal contract requires human review"

    def test_multiple_constitutional_rules_all_apply(
        self, default_ctx: UserContext, sample_policy_set: PolicySet
    ):
        """Multiple constitutional rules should all apply."""
        intent = Intent(
            domain="Legal",
            task="contract_review",
            audience="internal",
            impact="high",
            confidence=0.9,
        )
        # Both PII and LEGAL_CONTRACT
        risk = RiskSignals(signals=["PII", "LEGAL_CONTRACT"])

        decision = evaluate_governance(intent, risk, default_ctx, sample_policy_set)

        assert decision.hitl_mode == HITLMode.ESCALATE
        assert decision.provider_constraints.local_only is True
        assert "const_pii_local" in decision.policy_trigger_ids
        assert "const_legal_escalate" in decision.policy_trigger_ids


# ============================================================================
# Test: Policy Loader
# ============================================================================

class TestPolicyLoader:
    """Test the YAML policy loader."""

    def test_load_from_dict(self):
        """Test loading policies from a dictionary."""
        raw = {
            "constitutional_rules": [
                {
                    "id": "test_rule",
                    "name": "Test Rule",
                    "description": "A test rule",
                    "conditions": [
                        {"field": "intent.audience", "operator": "eq", "value": "public"}
                    ],
                    "action": {"hitl_mode": "DRAFT"},
                    "priority": 100,
                }
            ],
            "organization_rules": {
                "default": []
            },
            "department_rules": {},
        }

        loader = PolicyLoader()
        policy_set = loader.load_from_dict(raw)

        assert len(policy_set.constitutional_rules) == 1
        assert policy_set.constitutional_rules[0].id == "test_rule"
        assert policy_set.constitutional_rules[0].action.hitl_mode == HITLMode.DRAFT

    def test_empty_dict_returns_empty_policy_set(self):
        """Empty dict should return empty PolicySet."""
        loader = PolicyLoader()
        policy_set = loader.load_from_dict({})

        assert len(policy_set.constitutional_rules) == 0
        assert len(policy_set.organization_rules.default) == 0
        assert len(policy_set.department_rules) == 0


# ============================================================================
# Test: HITL Mode Priority (Most Restrictive Wins)
# ============================================================================

class TestHITLModePriority:
    """Test that most restrictive HITL mode wins."""

    def test_escalate_beats_draft(self, default_ctx: UserContext):
        """ESCALATE should beat DRAFT when both match."""
        policy_set = PolicySet(
            constitutional_rules=[],
            organization_rules=OrganizationRules(
                default=[
                    PolicyRule(
                        id="rule_draft",
                        name="Draft Rule",
                        description="",
                        conditions=[
                            RuleCondition(
                                field="intent.audience",
                                operator=ConditionOperator.EQUALS,
                                value="public",
                            )
                        ],
                        action=RuleAction(hitl_mode=HITLMode.DRAFT),
                    ),
                    PolicyRule(
                        id="rule_escalate",
                        name="Escalate Rule",
                        description="",
                        conditions=[
                            RuleCondition(
                                field="intent.impact",
                                operator=ConditionOperator.EQUALS,
                                value="high",
                            )
                        ],
                        action=RuleAction(hitl_mode=HITLMode.ESCALATE),
                    ),
                ]
            ),
        )

        intent = Intent(
            domain="General",
            task="announcement",
            audience="public",
            impact="high",
            confidence=0.9,
        )
        risk = RiskSignals(signals=[])

        decision = evaluate_governance(intent, risk, default_ctx, policy_set)

        assert decision.hitl_mode == HITLMode.ESCALATE

    def test_draft_beats_inform(self, default_ctx: UserContext):
        """DRAFT should beat INFORM when both could apply."""
        policy_set = PolicySet(
            organization_rules=OrganizationRules(
                default=[
                    PolicyRule(
                        id="rule_draft",
                        name="Draft Rule",
                        description="",
                        conditions=[
                            RuleCondition(
                                field="intent.audience",
                                operator=ConditionOperator.EQUALS,
                                value="public",
                            )
                        ],
                        action=RuleAction(hitl_mode=HITLMode.DRAFT),
                    ),
                ]
            ),
        )

        intent = Intent(
            domain="General",
            task="announcement",
            audience="public",
            impact="low",
            confidence=0.9,
        )
        risk = RiskSignals(signals=[])

        decision = evaluate_governance(intent, risk, default_ctx, policy_set)

        assert decision.hitl_mode == HITLMode.DRAFT


# ============================================================================
# Test: RiskSignals.contains() method
# ============================================================================

class TestRiskSignalsContains:
    """Test the RiskSignals.contains() method."""

    def test_contains_returns_true_when_present(self):
        """contains() should return True when signal is present."""
        risk = RiskSignals(signals=["PII", "LEGAL_CONTRACT"])
        assert risk.contains("PII") is True
        assert risk.contains("LEGAL_CONTRACT") is True

    def test_contains_returns_false_when_absent(self):
        """contains() should return False when signal is absent."""
        risk = RiskSignals(signals=["PII"])
        assert risk.contains("LEGAL_CONTRACT") is False

    def test_contains_empty_signals(self):
        """contains() should return False for empty signals."""
        risk = RiskSignals(signals=[])
        assert risk.contains("PII") is False

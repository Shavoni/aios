"""Unit tests for Simulation Mode."""

import pytest

from packages.core.schemas.models import HITLMode
from packages.core.simulation import (
    SimulationRunner,
    SimulationResult,
    BatchSimulationResult,
    simulate_batch,
)
from packages.core.governance import (
    ConditionOperator,
    DepartmentRules,
    OrganizationRules,
    PolicyRule,
    PolicySet,
    RuleAction,
    RuleCondition,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_policy_set() -> PolicySet:
    """Sample policy set for testing."""
    return PolicySet(
        constitutional_rules=[
            PolicyRule(
                id="const_pii_local",
                name="PII Local Only",
                description="PII must be processed locally",
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
            PolicyRule(
                id="const_legal_escalate",
                name="Legal Escalation",
                description="Legal matters require escalation",
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
            ]
        ),
    )


# ============================================================================
# Test: Tools Are Never Executed
# ============================================================================

class TestToolsNeverExecuted:
    """Verify that tools are NEVER executed in simulation mode."""

    def test_tools_executed_always_zero(self, sample_policy_set: PolicySet):
        """tools_executed should always be 0."""
        runner = SimulationRunner(policy_set=sample_policy_set)

        result = runner.simulate_batch(
            inputs=[
                {"text": "Draft a public statement about the partnership."},
                {"text": "Review this contract for legal issues."},
                {"text": "Look up employee salary information."},
            ],
            tenant_id="test-tenant",
        )

        assert result.tools_executed == 0

    def test_audit_stub_tools_always_empty(self, sample_policy_set: PolicySet):
        """audit_event_stub.tools_executed should always be empty list."""
        runner = SimulationRunner(policy_set=sample_policy_set)

        result = runner.simulate_single(
            text="Execute a dangerous command",
            tenant_id="test-tenant",
        )

        assert result.audit_event_stub["tools_executed"] == []

    def test_simulation_mode_flag_always_true(self, sample_policy_set: PolicySet):
        """audit_event_stub.simulation_mode should always be True."""
        runner = SimulationRunner(policy_set=sample_policy_set)

        result = runner.simulate_single(
            text="Do something",
            tenant_id="test-tenant",
        )

        assert result.audit_event_stub["simulation_mode"] is True


# ============================================================================
# Test: Deterministic Outputs
# ============================================================================

class TestDeterministicOutputs:
    """Verify that simulation outputs are deterministic."""

    def test_same_input_same_intent(self, sample_policy_set: PolicySet):
        """Same input should produce same intent classification."""
        runner = SimulationRunner(policy_set=sample_policy_set)

        text = "Draft a public statement about the partnership."

        result1 = runner.simulate_single(text=text, tenant_id="test")
        result2 = runner.simulate_single(text=text, tenant_id="test")

        assert result1.intent.domain == result2.intent.domain
        assert result1.intent.task == result2.intent.task
        assert result1.intent.audience == result2.intent.audience
        assert result1.intent.impact == result2.intent.impact

    def test_same_input_same_risk(self, sample_policy_set: PolicySet):
        """Same input should produce same risk signals."""
        runner = SimulationRunner(policy_set=sample_policy_set)

        text = "Review this NDA contract agreement."

        result1 = runner.simulate_single(text=text, tenant_id="test")
        result2 = runner.simulate_single(text=text, tenant_id="test")

        assert result1.risk.signals == result2.risk.signals

    def test_same_input_same_governance(self, sample_policy_set: PolicySet):
        """Same input should produce same governance decision."""
        runner = SimulationRunner(policy_set=sample_policy_set)

        text = "Draft a public statement about the partnership."

        result1 = runner.simulate_single(text=text, tenant_id="test")
        result2 = runner.simulate_single(text=text, tenant_id="test")

        assert result1.governance.hitl_mode == result2.governance.hitl_mode
        assert result1.governance.tools_allowed == result2.governance.tools_allowed
        assert result1.governance.policy_trigger_ids == result2.governance.policy_trigger_ids


# ============================================================================
# Test: Batch Simulation
# ============================================================================

class TestBatchSimulation:
    """Test batch simulation functionality."""

    def test_batch_returns_correct_count(self, sample_policy_set: PolicySet):
        """Batch should return correct number of results."""
        inputs = [
            {"text": "Question 1"},
            {"text": "Question 2"},
            {"text": "Question 3"},
        ]

        result = simulate_batch(
            inputs=inputs,
            tenant_id="test",
            policy_set=sample_policy_set,
        )

        assert result.total == 3
        assert len(result.results) == 3

    def test_batch_processes_each_input(self, sample_policy_set: PolicySet):
        """Each input should be processed independently."""
        inputs = [
            {"text": "Draft a public statement."},  # Should be DRAFT
            {"text": "Review this NDA contract."},  # Should be ESCALATE
            {"text": "What is the weather?"},       # Should be INFORM
        ]

        result = simulate_batch(
            inputs=inputs,
            tenant_id="test",
            policy_set=sample_policy_set,
        )

        # Public statement -> DRAFT
        assert result.results[0].governance.hitl_mode == HITLMode.DRAFT

        # Contract with LEGAL_CONTRACT risk -> ESCALATE
        assert result.results[1].governance.hitl_mode == HITLMode.ESCALATE

        # General question -> INFORM (default)
        assert result.results[2].governance.hitl_mode == HITLMode.INFORM

    def test_batch_with_user_context(self, sample_policy_set: PolicySet):
        """Batch should handle per-input user context."""
        inputs = [
            {"text": "Hello", "user_id": "user1", "department": "HR"},
            {"text": "World", "user_id": "user2", "department": "Finance"},
        ]

        result = simulate_batch(
            inputs=inputs,
            tenant_id="test",
            policy_set=sample_policy_set,
        )

        assert result.results[0].audit_event_stub["user_id"] == "user1"
        assert result.results[0].audit_event_stub["department"] == "HR"
        assert result.results[1].audit_event_stub["user_id"] == "user2"
        assert result.results[1].audit_event_stub["department"] == "Finance"


# ============================================================================
# Test: Policy Evaluation
# ============================================================================

class TestPolicyEvaluation:
    """Test that policies are correctly evaluated in simulation."""

    def test_public_statement_triggers_draft(self, sample_policy_set: PolicySet):
        """Public statement should trigger DRAFT mode."""
        runner = SimulationRunner(policy_set=sample_policy_set)

        result = runner.simulate_single(
            text="Draft a public statement about our new product.",
            tenant_id="test",
        )

        assert result.governance.hitl_mode == HITLMode.DRAFT
        assert result.governance.approval_required is True

    def test_legal_contract_triggers_escalate(self, sample_policy_set: PolicySet):
        """Legal contract should trigger ESCALATE mode."""
        runner = SimulationRunner(policy_set=sample_policy_set)

        result = runner.simulate_single(
            text="Review this NDA agreement contract.",
            tenant_id="test",
        )

        assert result.governance.hitl_mode == HITLMode.ESCALATE
        assert "const_legal_escalate" in result.governance.policy_trigger_ids

    def test_pii_triggers_local_only(self, sample_policy_set: PolicySet):
        """PII should trigger local_only constraint."""
        runner = SimulationRunner(policy_set=sample_policy_set)

        result = runner.simulate_single(
            text="Look up the employee's social security number and home address.",
            tenant_id="test",
        )

        assert result.governance.provider_constraints.local_only is True
        assert "const_pii_local" in result.governance.policy_trigger_ids

    def test_default_is_inform(self, sample_policy_set: PolicySet):
        """Default without matching policies should be INFORM."""
        runner = SimulationRunner(policy_set=sample_policy_set)

        result = runner.simulate_single(
            text="What is the capital of France?",
            tenant_id="test",
        )

        assert result.governance.hitl_mode == HITLMode.INFORM


# ============================================================================
# Test: Agent Selection
# ============================================================================

class TestAgentSelection:
    """Test agent selection in simulation."""

    def test_comms_domain_selects_communications_agent(self, sample_policy_set: PolicySet):
        """Comms domain should select communications_agent."""
        runner = SimulationRunner(policy_set=sample_policy_set)

        result = runner.simulate_single(
            text="Draft a public statement.",
            tenant_id="test",
        )

        assert result.agent_id == "communications_agent"

    def test_legal_domain_selects_legal_agent(self, sample_policy_set: PolicySet):
        """Legal domain should select legal_agent."""
        runner = SimulationRunner(policy_set=sample_policy_set)

        result = runner.simulate_single(
            text="Review this contract agreement.",
            tenant_id="test",
        )

        assert result.agent_id == "legal_agent"

    def test_general_domain_selects_research_agent(self, sample_policy_set: PolicySet):
        """General domain should select research_agent."""
        runner = SimulationRunner(policy_set=sample_policy_set)

        result = runner.simulate_single(
            text="xyz abc 123",  # Unknown text
            tenant_id="test",
        )

        assert result.agent_id == "research_agent"


# ============================================================================
# Test: Audit Event Stub
# ============================================================================

class TestAuditEventStub:
    """Test audit event stub structure."""

    def test_audit_stub_contains_required_fields(self, sample_policy_set: PolicySet):
        """Audit stub should contain all required fields."""
        runner = SimulationRunner(policy_set=sample_policy_set)

        result = runner.simulate_single(
            text="Test request",
            tenant_id="test-tenant",
            user_id="test-user",
            department="Engineering",
        )

        stub = result.audit_event_stub

        assert "request_id" in stub
        assert "tenant_id" in stub
        assert "user_id" in stub
        assert "department" in stub
        assert "timestamp" in stub
        assert "request_text" in stub
        assert "intent" in stub
        assert "risk_signals" in stub
        assert "governance" in stub
        assert "agent_id" in stub
        assert "simulation_mode" in stub
        assert "tools_executed" in stub

        assert stub["tenant_id"] == "test-tenant"
        assert stub["user_id"] == "test-user"
        assert stub["department"] == "Engineering"
        assert stub["simulation_mode"] is True

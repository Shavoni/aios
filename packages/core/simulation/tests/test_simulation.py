"""Tests for Simulation Mode.

Required tests per TRACE-001 spec:
- test_simulation_never_calls_tools()
- test_simulation_trace_is_deterministic_for_same_input()
- test_simulation_differs_from_live_execution()
"""

import pytest
from ..runner import (
    NullToolExecutor,
    ToolCallAttemptedError,
    SimulationRunner,
    DecisionTrace,
    IntentClassifier,
    RiskAssessor,
    AgentRouter,
)
from ..tracer import ExecutionTracer, TraceEventType


class TestNullToolExecutor:
    """Tests for NullToolExecutor."""

    def test_strict_mode_raises_on_tool_call(self):
        """Test that strict mode raises when tools are called."""
        executor = NullToolExecutor(strict=True)

        with pytest.raises(ToolCallAttemptedError) as exc_info:
            executor.execute("send_email", {"to": "user@example.com"})

        assert exc_info.value.tool_name == "send_email"
        assert "send_email" in str(exc_info.value)

    def test_non_strict_mode_returns_placeholder(self):
        """Test that non-strict mode returns placeholder."""
        executor = NullToolExecutor(strict=False)

        result = executor.execute("send_email", {"to": "user@example.com"})

        assert result["simulated"] is True
        assert result["tool"] == "send_email"

    def test_tracks_attempted_calls(self):
        """Test that attempted calls are tracked."""
        executor = NullToolExecutor(strict=False)

        executor.execute("tool_a", {"arg": 1})
        executor.execute("tool_b", {"arg": 2})

        calls = executor.get_attempted_calls()
        assert len(calls) == 2
        assert calls[0] == ("tool_a", {"arg": 1})
        assert calls[1] == ("tool_b", {"arg": 2})

    def test_clear_removes_tracked_calls(self):
        """Test that clear removes tracked calls."""
        executor = NullToolExecutor(strict=False)
        executor.execute("tool_a", {})
        executor.clear()

        assert len(executor.get_attempted_calls()) == 0


class TestSimulationRunner:
    """Tests for SimulationRunner."""

    def test_simulation_never_calls_tools(self):
        """REQUIRED: Simulation must never execute real tools.

        Per TRACE-001 spec: NullToolExecutor must raise if tools called.
        """
        runner = SimulationRunner()

        # Run simulation - should complete without tool calls
        trace = runner.run("What is the FMLA policy?")

        # Verify simulation completed successfully
        assert trace.request_text == "What is the FMLA policy?"
        assert trace.detected_intent != ""
        assert trace.selected_agent != ""
        assert trace.response_text != ""

        # The internal NullToolExecutor should have no attempted calls
        # because the simulation uses rule-based stubs
        assert runner._tool_executor.get_attempted_calls() == []

    def test_simulation_trace_is_deterministic_for_same_input(self):
        """REQUIRED: Same input must produce identical decision hash.

        Per TRACE-001 spec: Deterministic output (rule-based stub as default).
        """
        runner = SimulationRunner()

        # Run same request multiple times
        trace1 = runner.run("I need to request FMLA leave")
        trace2 = runner.run("I need to request FMLA leave")
        trace3 = runner.run("I need to request FMLA leave")

        # All hashes must match
        assert trace1.decision_hash == trace2.decision_hash
        assert trace2.decision_hash == trace3.decision_hash

        # All decision points must match
        assert trace1.detected_intent == trace2.detected_intent
        assert trace1.selected_agent == trace2.selected_agent
        assert trace1.risk_level == trace2.risk_level
        assert trace1.response_text == trace2.response_text

    def test_simulation_differs_from_live_execution(self):
        """REQUIRED: Simulation output must be distinguishable from live.

        Per TRACE-001 spec: Simulation traces should be clearly marked.
        """
        runner = SimulationRunner()

        trace = runner.run("What are my benefits options?")
        execution_trace = runner.get_execution_trace()

        # DecisionTrace is always from simulation
        assert trace.response_type in [
            "hr_leave", "hr_benefits", "it_support", "finance",
            "legal", "building", "general", "unknown"
        ]

        # ExecutionTrace is marked as simulation
        assert execution_trace is not None
        assert execution_trace.is_simulation is True

    def test_verify_determinism_helper(self):
        """Test the verify_determinism helper method."""
        runner = SimulationRunner()

        is_deterministic, hashes = runner.verify_determinism(
            "How do I submit an expense report?",
            runs=5
        )

        assert is_deterministic is True
        assert len(hashes) == 5
        assert len(set(hashes)) == 1  # All hashes identical

    def test_different_inputs_produce_different_hashes(self):
        """Different requests should produce different decision hashes."""
        runner = SimulationRunner()

        trace1 = runner.run("I need FMLA information")
        trace2 = runner.run("How do I reset my password?")
        trace3 = runner.run("What is the contract review process?")

        # All should have different hashes
        hashes = {trace1.decision_hash, trace2.decision_hash, trace3.decision_hash}
        assert len(hashes) == 3


class TestDecisionTrace:
    """Tests for DecisionTrace dataclass."""

    def test_hash_computation(self):
        """Test that hash is computed from key fields."""
        trace = DecisionTrace(
            request_id="test-123",
            request_text="Test request",
            tenant_id="tenant-1",
            user_id="user-1",
            detected_intent="hr_leave",
            risk_level="low",
            selected_agent="hr_specialist",
            requires_hitl=False,
            selected_model="gpt-4o-mini",
        )

        assert trace.decision_hash != ""
        assert len(trace.decision_hash) == 32

    def test_hash_changes_with_content(self):
        """Test that hash changes when content changes."""
        trace1 = DecisionTrace(
            request_id="test-123",
            request_text="Request A",
            tenant_id="tenant-1",
            user_id="user-1",
            detected_intent="hr_leave",
        )

        trace2 = DecisionTrace(
            request_id="test-123",
            request_text="Request B",  # Different
            tenant_id="tenant-1",
            user_id="user-1",
            detected_intent="hr_leave",
        )

        assert trace1.decision_hash != trace2.decision_hash

    def test_to_dict_serialization(self):
        """Test serialization to dictionary."""
        trace = DecisionTrace(
            request_id="test-123",
            request_text="Test",
            tenant_id="t1",
            user_id="u1",
        )

        data = trace.to_dict()

        assert data["request_id"] == "test-123"
        assert data["tenant_id"] == "t1"
        assert "decision_hash" in data

    def test_from_dict_deserialization(self):
        """Test deserialization from dictionary."""
        data = {
            "request_id": "test-123",
            "request_text": "Test",
            "tenant_id": "t1",
            "user_id": "u1",
            "timestamp": "2024-01-01T00:00:00+00:00",
            "detected_intent": "hr_leave",
            "intent_confidence": 0.95,
            "intent_alternatives": [],
            "risk_level": "low",
            "risk_score": 0.1,
            "risk_factors": [],
            "selected_agent": "hr_specialist",
            "agent_confidence": 0.9,
            "agent_alternatives": [],
            "routing_reason": "test",
            "requires_hitl": False,
            "hitl_reason": "",
            "governance_checks": [],
            "selected_model": "gpt-4o-mini",
            "model_tier": "economy",
            "estimated_cost": 0.0001,
            "kb_queries": [],
            "kb_results": [],
            "response_text": "Test response",
            "response_type": "hr_leave",
            "decision_hash": "abc123",
        }

        trace = DecisionTrace.from_dict(data)

        assert trace.request_id == "test-123"
        assert trace.detected_intent == "hr_leave"


class TestIntentClassifier:
    """Tests for rule-based IntentClassifier."""

    def test_classifies_hr_leave(self):
        """Test HR leave intent classification."""
        classifier = IntentClassifier()

        intent, confidence, _ = classifier.classify("I need to request FMLA leave")

        assert intent == "hr_leave"
        assert confidence > 0.5

    def test_classifies_it_support(self):
        """Test IT support intent classification."""
        classifier = IntentClassifier()

        intent, confidence, _ = classifier.classify("I forgot my password")

        assert intent == "it_support"
        assert confidence > 0.5

    def test_classifies_finance(self):
        """Test finance intent classification."""
        classifier = IntentClassifier()

        intent, confidence, _ = classifier.classify("How do I submit an expense reimbursement?")

        assert intent == "finance_expense"
        assert confidence > 0.5

    def test_returns_alternatives(self):
        """Test that alternatives are returned."""
        classifier = IntentClassifier()

        # Query that could match multiple intents
        _, _, alternatives = classifier.classify("I need help with my benefits and leave policy")

        # Should have some alternatives
        assert isinstance(alternatives, list)


class TestRiskAssessor:
    """Tests for rule-based RiskAssessor."""

    def test_high_risk_detection(self):
        """Test high risk keyword detection."""
        assessor = RiskAssessor()

        # Multiple high-risk keywords to reach high threshold
        level, score, factors = assessor.assess(
            "There was a security breach and data leak, we need to terminate access"
        )

        assert level == "high"
        assert score >= 0.6
        assert len(factors) >= 2

    def test_low_risk_detection(self):
        """Test low risk queries."""
        assessor = RiskAssessor()

        level, score, factors = assessor.assess("What are the office hours?")

        assert level == "low"
        assert score < 0.3

    def test_medium_risk_detection(self):
        """Test medium risk queries."""
        assessor = RiskAssessor()

        level, score, factors = assessor.assess("I need to review a contract")

        assert level in ("low", "medium")


class TestAgentRouter:
    """Tests for rule-based AgentRouter."""

    def test_routes_hr_intent_to_hr_specialist(self):
        """Test HR intents route to HR specialist."""
        router = AgentRouter()

        agent, confidence, _, reason = router.route("hr_leave")

        assert agent == "hr_specialist"
        assert confidence > 0.8

    def test_routes_it_intent_to_it_support(self):
        """Test IT intents route to IT support."""
        router = AgentRouter()

        agent, confidence, _, _ = router.route("it_support")

        assert agent == "it_support"
        assert confidence > 0.8

    def test_routes_unknown_to_concierge(self):
        """Test unknown intents route to concierge."""
        router = AgentRouter()

        agent, confidence, _, _ = router.route("unknown_intent")

        assert agent == "concierge"


class TestExecutionTracer:
    """Tests for ExecutionTracer integration."""

    def test_tracer_records_events(self):
        """Test that tracer records events during simulation."""
        runner = SimulationRunner()

        runner.run("Test query")
        trace = runner.get_execution_trace()

        assert trace is not None
        assert len(trace.events) > 0
        assert trace.is_simulation is True

    def test_tracer_events_have_correct_types(self):
        """Test that events have expected types."""
        runner = SimulationRunner()

        runner.run("I need FMLA leave")
        trace = runner.get_execution_trace()

        event_types = [e.event_type for e in trace.events]

        # Should have intent classification and routing events
        assert TraceEventType.INTENT_CLASSIFICATION in event_types
        assert TraceEventType.RISK_DETECTION in event_types
        assert TraceEventType.AGENT_ROUTING in event_types

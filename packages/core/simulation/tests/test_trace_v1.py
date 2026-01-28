"""Tests for TRACE-001 Strict Schema and Determinism.

Required tests per TRACE-001 spec:
- test_golden_traces (>=15 fixtures)
- test_trace_deterministic_across_100_runs
- test_null_tool_executor_blocks_all_tools
- test_tool_call_blocked_step_logged
"""

import pytest
import json
from pathlib import Path

from ..schema import (
    TRACE_VERSION,
    DecisionTraceV1,
    TraceStepV1,
    TraceStepType,
    ConfidenceScoreV1,
    IntentResultV1,
    RiskResultV1,
    GovernanceResultV1,
    RoutingResultV1,
    ModelSelectionV1,
    ToolCallBlockedV1,
    create_trace,
)
from ..runner import (
    SimulationRunner,
    NullToolExecutor,
    ToolCallAttemptedError,
)


class TestDecisionTraceV1Schema:
    """Tests for the strict Pydantic schema."""

    def test_trace_version_is_set(self):
        """Test that trace version is set correctly."""
        assert TRACE_VERSION == "1.0.0"

        trace = create_trace(
            request_text="Test",
            tenant_id="tenant-1",
        )
        assert trace.trace_version == "1.0.0"

    def test_confidence_score_validation(self):
        """Test confidence score validation."""
        # Valid scores
        score = ConfidenceScoreV1(score=0.85, level="high", reason="Test")
        assert score.score == 0.85
        assert score.level == "high"

        # Auto-level setting
        score2 = ConfidenceScoreV1(score=0.5, level="low", reason="Test")
        assert score2.level == "low"  # Should be auto-set based on score

    def test_confidence_score_rounding(self):
        """Test that scores are rounded for determinism."""
        score = ConfidenceScoreV1(score=0.123456789, level="low", reason="Test")
        assert score.score == 0.123457  # Rounded to 6 decimal places

    def test_trace_hash_excludes_timestamps(self):
        """Test that timestamps are excluded from hash computation."""
        trace1 = create_trace(
            request_text="Test request",
            tenant_id="tenant-1",
            user_id="user-1",
        )
        trace1.intent = IntentResultV1(
            primary_intent="hr_leave",
            confidence=ConfidenceScoreV1(score=0.9, level="high"),
        )
        trace1.finalize()

        # Create another trace with same content but different time
        import time
        time.sleep(0.01)  # Ensure different timestamp

        trace2 = create_trace(
            request_text="Test request",
            tenant_id="tenant-1",
            user_id="user-1",
        )
        trace2.intent = IntentResultV1(
            primary_intent="hr_leave",
            confidence=ConfidenceScoreV1(score=0.9, level="high"),
        )
        trace2.finalize()

        # Timestamps should be different
        assert trace1.created_at != trace2.created_at

        # But hashes should be the same
        assert trace1.trace_hash == trace2.trace_hash

    def test_canonical_json_sorted_keys(self):
        """Test that canonical JSON uses sorted keys."""
        trace = create_trace(
            request_text="Test",
            tenant_id="tenant-1",
        )
        trace.intent = IntentResultV1(
            primary_intent="test",
            confidence=ConfidenceScoreV1(score=0.8, level="medium"),
        )

        canonical = trace.to_canonical_json()

        # Keys should be sorted
        data = json.loads(canonical)
        keys = list(data.keys())
        assert keys == sorted(keys)

    def test_risk_result_validation(self):
        """Test risk result validation."""
        risk = RiskResultV1(
            level="high",
            score=0.75,
            factors=["confidential", "legal"],
        )
        assert risk.level == "high"
        assert risk.score == 0.75

    def test_model_selection_cost_rounding(self):
        """Test that costs are rounded for determinism."""
        model = ModelSelectionV1(
            model_id="gpt-4o",
            tier="standard",
            estimated_cost_usd=0.00312345678,
        )
        assert model.estimated_cost_usd == 0.003123  # Rounded


class TestGoldenTraces:
    """Tests against golden trace fixtures."""

    @pytest.fixture
    def golden_fixtures(self):
        """Load golden trace fixtures."""
        fixtures_path = Path(__file__).parent.parent / "fixtures" / "golden_traces.json"
        with open(fixtures_path) as f:
            return json.load(f)

    def test_golden_fixtures_exist(self, golden_fixtures):
        """Test that golden fixtures file exists with at least 15 fixtures."""
        assert "fixtures" in golden_fixtures
        assert len(golden_fixtures["fixtures"]) >= 15

    def test_golden_traces(self, golden_fixtures):
        """REQUIRED: Test all golden trace fixtures produce expected results."""
        runner = SimulationRunner()

        for fixture in golden_fixtures["fixtures"]:
            trace = runner.run_v1(
                request_text=fixture["request_text"],
                tenant_id=fixture["tenant_id"],
                user_id=fixture["user_id"],
            )

            expected = fixture["expected"]

            # Verify intent classification
            assert trace.intent is not None
            assert trace.intent.primary_intent == expected["intent"], \
                f"Fixture {fixture['id']}: Expected intent {expected['intent']}, got {trace.intent.primary_intent}"

            # Verify risk level
            assert trace.risk is not None
            assert trace.risk.level == expected["risk_level"], \
                f"Fixture {fixture['id']}: Expected risk {expected['risk_level']}, got {trace.risk.level}"

            # Verify agent routing
            assert trace.routing is not None
            assert trace.routing.selected_agent == expected["agent"], \
                f"Fixture {fixture['id']}: Expected agent {expected['agent']}, got {trace.routing.selected_agent}"

            # Verify model tier
            assert trace.model_selection is not None
            assert trace.model_selection.tier == expected["model_tier"], \
                f"Fixture {fixture['id']}: Expected tier {expected['model_tier']}, got {trace.model_selection.tier}"

            # Verify HITL requirement
            assert trace.governance is not None
            assert trace.governance.requires_hitl == expected["requires_hitl"], \
                f"Fixture {fixture['id']}: Expected HITL {expected['requires_hitl']}, got {trace.governance.requires_hitl}"


class TestDeterminism:
    """Tests for deterministic simulation."""

    def test_trace_deterministic_across_100_runs(self):
        """REQUIRED: Same input produces identical hash across 100 runs."""
        runner = SimulationRunner()

        is_deterministic, hashes = runner.verify_determinism_v1(
            request_text="I need to request FMLA leave for medical reasons",
            runs=100,
            tenant_id="determinism-test",
        )

        assert is_deterministic, f"Simulation not deterministic! Got {len(set(hashes))} unique hashes"
        assert len(hashes) == 100
        assert len(set(hashes)) == 1

    def test_different_inputs_produce_different_hashes(self):
        """Different inputs should produce different hashes."""
        runner = SimulationRunner()

        trace1 = runner.run_v1("FMLA leave request", tenant_id="test")
        trace2 = runner.run_v1("Password reset needed", tenant_id="test")
        trace3 = runner.run_v1("Contract review request", tenant_id="test")

        hashes = {trace1.trace_hash, trace2.trace_hash, trace3.trace_hash}
        assert len(hashes) == 3, "Different inputs should produce different hashes"

    def test_tenant_affects_hash(self):
        """Different tenants with same request should produce different hashes."""
        runner = SimulationRunner()

        trace1 = runner.run_v1("Test request", tenant_id="tenant-a")
        trace2 = runner.run_v1("Test request", tenant_id="tenant-b")

        assert trace1.trace_hash != trace2.trace_hash

    def test_user_affects_hash(self):
        """Different users with same request should produce different hashes."""
        runner = SimulationRunner()

        trace1 = runner.run_v1("Test request", tenant_id="test", user_id="user-a")
        trace2 = runner.run_v1("Test request", tenant_id="test", user_id="user-b")

        assert trace1.trace_hash != trace2.trace_hash


class TestNullToolExecutor:
    """Tests for NullToolExecutor blocking all tools."""

    def test_null_tool_executor_blocks_all_tools(self):
        """REQUIRED: NullToolExecutor must block ALL tool calls."""
        executor = NullToolExecutor(strict=True)

        tools_to_test = [
            ("send_email", {"to": "user@example.com", "body": "Test"}),
            ("execute_sql", {"query": "SELECT * FROM users"}),
            ("write_file", {"path": "/etc/passwd", "content": "hack"}),
            ("call_api", {"url": "https://api.example.com", "method": "POST"}),
            ("run_shell", {"command": "rm -rf /"}),
            ("fetch_url", {"url": "https://malicious.com"}),
        ]

        for tool_name, args in tools_to_test:
            with pytest.raises(ToolCallAttemptedError) as exc_info:
                executor.execute(tool_name, args)

            assert exc_info.value.tool_name == tool_name
            assert "simulation mode" in str(exc_info.value).lower()

    def test_tool_call_blocked_step_logged(self):
        """REQUIRED: Blocked tool calls must be logged as trace steps."""
        trace = create_trace(
            request_text="Test",
            tenant_id="test",
        )

        executor = NullToolExecutor(strict=False, trace=trace)

        # Execute some tools (non-strict mode to continue after each)
        executor.execute("send_email", {"to": "test@example.com"})
        executor.execute("execute_sql", {"query": "SELECT 1"})

        # Verify blocked tools are logged
        assert len(trace.blocked_tools) == 2
        assert trace.blocked_tools[0].tool_name == "send_email"
        assert trace.blocked_tools[1].tool_name == "execute_sql"

        # Verify trace steps are added
        blocked_steps = [
            s for s in trace.steps
            if s.step_type == TraceStepType.TOOL_CALL_BLOCKED
        ]
        assert len(blocked_steps) == 2

    def test_blocked_tool_includes_arguments(self):
        """Blocked tool record should include the attempted arguments."""
        trace = create_trace(request_text="Test", tenant_id="test")
        executor = NullToolExecutor(strict=False, trace=trace)

        executor.execute("api_call", {"url": "https://api.example.com", "key": "secret"})

        blocked = trace.blocked_tools[0]
        assert blocked.arguments["url"] == "https://api.example.com"
        assert blocked.arguments["key"] == "secret"

    def test_get_blocked_tools(self):
        """Test retrieving list of blocked tools."""
        executor = NullToolExecutor(strict=False)

        executor.execute("tool_a", {"arg": 1})
        executor.execute("tool_b", {"arg": 2})

        blocked = executor.get_blocked_tools()
        assert len(blocked) == 2
        assert blocked[0].tool_name == "tool_a"
        assert blocked[1].tool_name == "tool_b"


class TestSimulationRunnerV1:
    """Tests for SimulationRunner with V1 schema."""

    def test_run_v1_returns_decision_trace_v1(self):
        """Test that run_v1 returns proper DecisionTraceV1."""
        runner = SimulationRunner()

        trace = runner.run_v1(
            request_text="I need FMLA leave",
            tenant_id="test-tenant",
            user_id="test-user",
        )

        assert isinstance(trace, DecisionTraceV1)
        assert trace.trace_version == "1.0.0"
        assert trace.trace_hash != ""

    def test_run_v1_populates_all_fields(self):
        """Test that run_v1 populates all required fields."""
        runner = SimulationRunner()

        trace = runner.run_v1(
            request_text="Help me with my benefits",
            tenant_id="test-tenant",
        )

        # Request info
        assert trace.request_text == "Help me with my benefits"
        assert trace.tenant_id == "test-tenant"

        # Classification results
        assert trace.intent is not None
        assert trace.risk is not None
        assert trace.governance is not None
        assert trace.routing is not None
        assert trace.model_selection is not None

        # Steps
        assert len(trace.steps) > 0

        # Response
        assert trace.response_text != ""
        assert trace.response_type != ""

        # Finalization
        assert trace.success is True
        assert trace.trace_hash != ""

    def test_run_v1_includes_trace_steps(self):
        """Test that run_v1 includes expected trace steps."""
        runner = SimulationRunner()

        trace = runner.run_v1(
            request_text="Password reset",
            tenant_id="test",
        )

        step_types = [s.step_type for s in trace.steps]

        assert TraceStepType.INTENT_CLASSIFICATION in step_types
        assert TraceStepType.RISK_ASSESSMENT in step_types
        assert TraceStepType.GOVERNANCE_CHECK in step_types
        assert TraceStepType.AGENT_ROUTING in step_types
        assert TraceStepType.RESPONSE_GENERATION in step_types

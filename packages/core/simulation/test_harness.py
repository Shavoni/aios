"""Test Harness for Simulation Mode.

Provides:
- Test fixture generation from traces
- Deterministic replay and verification
- Regression test suite generation
- Coverage reporting
"""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Callable
from enum import Enum

from packages.core.simulation.tracer import (
    ExecutionTrace,
    ExecutionTracer,
    TraceEventType,
    TraceStore,
    get_trace_store,
)


class TestResult(str, Enum):
    """Test execution result."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class TestCase:
    """A single test case generated from a trace."""

    id: str
    name: str
    description: str

    # Input
    tenant_id: str
    user_id: str
    request_text: str
    user_context: dict[str, Any] = field(default_factory=dict)

    # Expected outputs
    expected_agent_id: str = ""
    expected_domain: str = ""
    expected_hitl_mode: str = ""
    expected_tools: list[str] = field(default_factory=list)

    # Validation rules
    must_contain_keywords: list[str] = field(default_factory=list)
    must_not_contain_keywords: list[str] = field(default_factory=list)
    max_latency_ms: float = 5000.0
    max_cost_usd: float = 0.10

    # Metadata
    source_trace_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "request_text": self.request_text,
            "user_context": self.user_context,
            "expected_agent_id": self.expected_agent_id,
            "expected_domain": self.expected_domain,
            "expected_hitl_mode": self.expected_hitl_mode,
            "expected_tools": self.expected_tools,
            "must_contain_keywords": self.must_contain_keywords,
            "must_not_contain_keywords": self.must_not_contain_keywords,
            "max_latency_ms": self.max_latency_ms,
            "max_cost_usd": self.max_cost_usd,
            "source_trace_id": self.source_trace_id,
            "created_at": self.created_at,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TestCase:
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            tenant_id=data["tenant_id"],
            user_id=data.get("user_id", "anonymous"),
            request_text=data["request_text"],
            user_context=data.get("user_context", {}),
            expected_agent_id=data.get("expected_agent_id", ""),
            expected_domain=data.get("expected_domain", ""),
            expected_hitl_mode=data.get("expected_hitl_mode", ""),
            expected_tools=data.get("expected_tools", []),
            must_contain_keywords=data.get("must_contain_keywords", []),
            must_not_contain_keywords=data.get("must_not_contain_keywords", []),
            max_latency_ms=data.get("max_latency_ms", 5000.0),
            max_cost_usd=data.get("max_cost_usd", 0.10),
            source_trace_id=data.get("source_trace_id", ""),
            created_at=data.get("created_at", ""),
            tags=data.get("tags", []),
        )

    @classmethod
    def from_trace(cls, trace: ExecutionTrace, name: str = "") -> TestCase:
        """Generate a test case from an execution trace."""
        # Extract expected values from trace events
        expected_agent = ""
        expected_domain = ""
        expected_hitl = ""

        for event in trace.events:
            if event.event_type == TraceEventType.AGENT_SELECTION:
                expected_agent = event.output_data.get("agent_id", "")
            if event.event_type == TraceEventType.INTENT_CLASSIFICATION:
                expected_domain = event.output_data.get("domain", "")
            if event.event_type == TraceEventType.GOVERNANCE_CHECK:
                expected_hitl = event.output_data.get("hitl_mode", "")

        return cls(
            id=f"test_{trace.id[:8]}",
            name=name or f"Test from trace {trace.id[:8]}",
            description=f"Auto-generated from trace {trace.id}",
            tenant_id=trace.tenant_id,
            user_id=trace.user_id,
            request_text=trace.request_text,
            expected_agent_id=expected_agent,
            expected_domain=expected_domain,
            expected_hitl_mode=expected_hitl,
            expected_tools=trace.tools_executed.copy(),
            max_latency_ms=trace.total_duration_ms * 1.5,  # 50% buffer
            max_cost_usd=trace.llm_cost_usd * 2.0,  # 100% buffer
            source_trace_id=trace.id,
        )


@dataclass
class TestRunResult:
    """Result of running a single test case."""

    test_id: str
    result: TestResult
    actual_trace: ExecutionTrace | None = None

    # Assertions
    assertions: list[dict[str, Any]] = field(default_factory=list)
    passed_assertions: int = 0
    failed_assertions: int = 0

    # Metrics
    duration_ms: float = 0.0
    error_message: str = ""

    def add_assertion(
        self,
        name: str,
        expected: Any,
        actual: Any,
        passed: bool,
    ) -> None:
        """Add an assertion result."""
        self.assertions.append({
            "name": name,
            "expected": expected,
            "actual": actual,
            "passed": passed,
        })
        if passed:
            self.passed_assertions += 1
        else:
            self.failed_assertions += 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_id": self.test_id,
            "result": self.result.value,
            "assertions": self.assertions,
            "passed_assertions": self.passed_assertions,
            "failed_assertions": self.failed_assertions,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
            "trace_id": self.actual_trace.id if self.actual_trace else None,
        }


@dataclass
class TestSuiteResult:
    """Result of running a test suite."""

    suite_name: str
    started_at: str
    finished_at: str = ""

    # Results
    results: list[TestRunResult] = field(default_factory=list)
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0

    # Metrics
    total_duration_ms: float = 0.0
    total_cost_usd: float = 0.0

    def add_result(self, result: TestRunResult) -> None:
        """Add a test result."""
        self.results.append(result)
        self.total_tests += 1

        if result.result == TestResult.PASSED:
            self.passed += 1
        elif result.result == TestResult.FAILED:
            self.failed += 1
        elif result.result == TestResult.SKIPPED:
            self.skipped += 1
        else:
            self.errors += 1

        self.total_duration_ms += result.duration_ms
        if result.actual_trace:
            self.total_cost_usd += result.actual_trace.llm_cost_usd

    def to_dict(self) -> dict[str, Any]:
        return {
            "suite_name": self.suite_name,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "total_tests": self.total_tests,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "errors": self.errors,
            "pass_rate": self.passed / self.total_tests if self.total_tests > 0 else 0,
            "total_duration_ms": self.total_duration_ms,
            "total_cost_usd": self.total_cost_usd,
            "results": [r.to_dict() for r in self.results],
        }

    def to_report(self) -> str:
        """Generate human-readable test report."""
        lines = [
            "=" * 80,
            f"TEST SUITE REPORT: {self.suite_name}",
            "=" * 80,
            "",
            f"Started: {self.started_at}",
            f"Finished: {self.finished_at}",
            f"Duration: {self.total_duration_ms:.2f}ms",
            f"Total Cost: ${self.total_cost_usd:.4f}",
            "",
            "-" * 80,
            "SUMMARY",
            "-" * 80,
            f"Total Tests: {self.total_tests}",
            f"Passed: {self.passed} ({self.passed/self.total_tests*100:.1f}%)" if self.total_tests else "Passed: 0",
            f"Failed: {self.failed}",
            f"Skipped: {self.skipped}",
            f"Errors: {self.errors}",
            "",
        ]

        if self.failed > 0 or self.errors > 0:
            lines.extend([
                "-" * 80,
                "FAILURES",
                "-" * 80,
            ])
            for result in self.results:
                if result.result in (TestResult.FAILED, TestResult.ERROR):
                    lines.append(f"  [{result.result.value.upper()}] {result.test_id}")
                    if result.error_message:
                        lines.append(f"    Error: {result.error_message}")
                    for assertion in result.assertions:
                        if not assertion["passed"]:
                            lines.append(f"    - {assertion['name']}")
                            lines.append(f"      Expected: {assertion['expected']}")
                            lines.append(f"      Actual: {assertion['actual']}")
            lines.append("")

        lines.append("=" * 80)
        return "\n".join(lines)


class TestHarness:
    """Test harness for running simulation tests."""

    def __init__(
        self,
        storage_path: Path | None = None,
        simulation_runner: Callable | None = None,
    ):
        self._storage_path = storage_path or Path("data/tests")
        self._storage_path.mkdir(parents=True, exist_ok=True)

        self._test_cases: dict[str, TestCase] = {}
        self._simulation_runner = simulation_runner

        self._load_test_cases()

    def _load_test_cases(self) -> None:
        """Load test cases from storage."""
        for test_file in self._storage_path.glob("*.json"):
            try:
                data = json.loads(test_file.read_text())
                if "id" in data and "request_text" in data:
                    self._test_cases[data["id"]] = TestCase.from_dict(data)
            except Exception:
                continue

    def _save_test_case(self, test_case: TestCase) -> None:
        """Save a test case to storage."""
        test_file = self._storage_path / f"{test_case.id}.json"
        test_file.write_text(json.dumps(test_case.to_dict(), indent=2))

    def set_simulation_runner(self, runner: Callable) -> None:
        """Set the simulation runner function."""
        self._simulation_runner = runner

    # =========================================================================
    # Test Case Management
    # =========================================================================

    def create_test_case(
        self,
        name: str,
        request_text: str,
        tenant_id: str = "test",
        **kwargs,
    ) -> TestCase:
        """Create a new test case."""
        test_id = f"test_{hashlib.md5(request_text.encode()).hexdigest()[:8]}"

        test_case = TestCase(
            id=test_id,
            name=name,
            description=kwargs.get("description", ""),
            tenant_id=tenant_id,
            user_id=kwargs.get("user_id", "test_user"),
            request_text=request_text,
            expected_agent_id=kwargs.get("expected_agent_id", ""),
            expected_domain=kwargs.get("expected_domain", ""),
            expected_hitl_mode=kwargs.get("expected_hitl_mode", ""),
            tags=kwargs.get("tags", []),
        )

        self._test_cases[test_id] = test_case
        self._save_test_case(test_case)

        return test_case

    def create_from_trace(self, trace: ExecutionTrace, name: str = "") -> TestCase:
        """Create a test case from an execution trace."""
        test_case = TestCase.from_trace(trace, name)
        self._test_cases[test_case.id] = test_case
        self._save_test_case(test_case)
        return test_case

    def get_test_case(self, test_id: str) -> TestCase | None:
        """Get a test case by ID."""
        return self._test_cases.get(test_id)

    def list_test_cases(self, tags: list[str] | None = None) -> list[TestCase]:
        """List test cases with optional tag filtering."""
        results = []
        for test_case in self._test_cases.values():
            if tags:
                if any(tag in test_case.tags for tag in tags):
                    results.append(test_case)
            else:
                results.append(test_case)
        return results

    def delete_test_case(self, test_id: str) -> bool:
        """Delete a test case."""
        if test_id in self._test_cases:
            del self._test_cases[test_id]
            test_file = self._storage_path / f"{test_id}.json"
            if test_file.exists():
                test_file.unlink()
            return True
        return False

    # =========================================================================
    # Test Execution
    # =========================================================================

    def run_test(self, test_case: TestCase) -> TestRunResult:
        """Run a single test case."""
        result = TestRunResult(test_id=test_case.id, result=TestResult.PASSED)

        if not self._simulation_runner:
            result.result = TestResult.SKIPPED
            result.error_message = "No simulation runner configured"
            return result

        try:
            # Run simulation
            tracer = ExecutionTracer(
                tenant_id=test_case.tenant_id,
                user_id=test_case.user_id,
                request_text=test_case.request_text,
                is_simulation=True,
            )

            # Execute simulation
            sim_result = self._simulation_runner(
                text=test_case.request_text,
                tenant_id=test_case.tenant_id,
                tracer=tracer,
            )

            trace = tracer.finish(
                response=sim_result.get("response", ""),
                success=sim_result.get("success", True),
            )

            result.actual_trace = trace
            result.duration_ms = trace.total_duration_ms

            # Run assertions
            self._run_assertions(test_case, trace, result)

            # Determine final result
            if result.failed_assertions > 0:
                result.result = TestResult.FAILED

        except Exception as e:
            result.result = TestResult.ERROR
            result.error_message = str(e)

        return result

    def _run_assertions(
        self,
        test_case: TestCase,
        trace: ExecutionTrace,
        result: TestRunResult,
    ) -> None:
        """Run all assertions for a test case."""
        # Check agent selection
        if test_case.expected_agent_id:
            actual_agent = ""
            for event in trace.events:
                if event.event_type == TraceEventType.AGENT_SELECTION:
                    actual_agent = event.output_data.get("agent_id", "")
                    break
            result.add_assertion(
                name="agent_id",
                expected=test_case.expected_agent_id,
                actual=actual_agent,
                passed=actual_agent == test_case.expected_agent_id,
            )

        # Check domain
        if test_case.expected_domain:
            actual_domain = ""
            for event in trace.events:
                if event.event_type == TraceEventType.INTENT_CLASSIFICATION:
                    actual_domain = event.output_data.get("domain", "")
                    break
            result.add_assertion(
                name="domain",
                expected=test_case.expected_domain,
                actual=actual_domain,
                passed=actual_domain == test_case.expected_domain,
            )

        # Check HITL mode
        if test_case.expected_hitl_mode:
            actual_hitl = ""
            for event in trace.events:
                if event.event_type == TraceEventType.GOVERNANCE_CHECK:
                    actual_hitl = event.output_data.get("hitl_mode", "")
                    break
            result.add_assertion(
                name="hitl_mode",
                expected=test_case.expected_hitl_mode,
                actual=actual_hitl,
                passed=actual_hitl == test_case.expected_hitl_mode,
            )

        # Check latency
        result.add_assertion(
            name="latency",
            expected=f"<= {test_case.max_latency_ms}ms",
            actual=f"{trace.total_duration_ms:.2f}ms",
            passed=trace.total_duration_ms <= test_case.max_latency_ms,
        )

        # Check cost
        result.add_assertion(
            name="cost",
            expected=f"<= ${test_case.max_cost_usd:.4f}",
            actual=f"${trace.llm_cost_usd:.4f}",
            passed=trace.llm_cost_usd <= test_case.max_cost_usd,
        )

        # Check keyword containment
        for keyword in test_case.must_contain_keywords:
            result.add_assertion(
                name=f"contains_{keyword}",
                expected=f"Response contains '{keyword}'",
                actual=keyword in trace.final_response,
                passed=keyword.lower() in trace.final_response.lower(),
            )

        for keyword in test_case.must_not_contain_keywords:
            result.add_assertion(
                name=f"not_contains_{keyword}",
                expected=f"Response does not contain '{keyword}'",
                actual=keyword not in trace.final_response,
                passed=keyword.lower() not in trace.final_response.lower(),
            )

    def run_suite(
        self,
        suite_name: str = "default",
        tags: list[str] | None = None,
        test_ids: list[str] | None = None,
    ) -> TestSuiteResult:
        """Run a suite of tests."""
        suite_result = TestSuiteResult(
            suite_name=suite_name,
            started_at=datetime.now(UTC).isoformat(),
        )

        # Get tests to run
        if test_ids:
            tests = [self._test_cases[tid] for tid in test_ids if tid in self._test_cases]
        else:
            tests = self.list_test_cases(tags=tags)

        # Run each test
        for test_case in tests:
            test_result = self.run_test(test_case)
            suite_result.add_result(test_result)

        suite_result.finished_at = datetime.now(UTC).isoformat()

        return suite_result

    # =========================================================================
    # Fixture Generation
    # =========================================================================

    def generate_fixtures_from_traces(
        self,
        trace_ids: list[str] | None = None,
        limit: int = 50,
    ) -> list[TestCase]:
        """Generate test fixtures from stored traces."""
        store = get_trace_store()
        fixtures = []

        traces = store.list_traces(limit=limit)

        for trace_info in traces:
            if trace_ids and trace_info["id"] not in trace_ids:
                continue

            trace = store.load(trace_info["id"])
            if trace and trace.success:
                test_case = self.create_from_trace(trace)
                fixtures.append(test_case)

        return fixtures

    def export_fixtures(self, output_path: Path) -> int:
        """Export all test fixtures to a file."""
        fixtures = [tc.to_dict() for tc in self._test_cases.values()]
        output_path.write_text(json.dumps(fixtures, indent=2))
        return len(fixtures)

    def import_fixtures(self, input_path: Path) -> int:
        """Import test fixtures from a file."""
        data = json.loads(input_path.read_text())
        count = 0
        for item in data:
            test_case = TestCase.from_dict(item)
            self._test_cases[test_case.id] = test_case
            self._save_test_case(test_case)
            count += 1
        return count


# Singleton
_test_harness: TestHarness | None = None


def get_test_harness() -> TestHarness:
    """Get the test harness singleton."""
    global _test_harness
    if _test_harness is None:
        _test_harness = TestHarness()
    return _test_harness


__all__ = [
    "TestResult",
    "TestCase",
    "TestRunResult",
    "TestSuiteResult",
    "TestHarness",
    "get_test_harness",
]

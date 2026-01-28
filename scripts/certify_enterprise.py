#!/usr/bin/env python3
"""Enterprise Certification Command.

Runs all enterprise tests and prints a comprehensive report.

Usage:
    python scripts/certify_enterprise.py
    python -m scripts.certify_enterprise
"""

from __future__ import annotations

import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, UTC
from pathlib import Path
from typing import Any


@dataclass
class TestResult:
    """Result of a test module."""
    module: str
    ticket: str
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.skipped

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.passed / self.total * 100


@dataclass
class CertificationReport:
    """Complete certification report."""
    timestamp: str
    results: list[TestResult] = field(default_factory=list)
    total_passed: int = 0
    total_failed: int = 0
    total_skipped: int = 0
    total_duration: float = 0.0
    certified: bool = False

    def add_result(self, result: TestResult) -> None:
        self.results.append(result)
        self.total_passed += result.passed
        self.total_failed += result.failed
        self.total_skipped += result.skipped
        self.total_duration += result.duration_seconds

    @property
    def total_tests(self) -> int:
        return self.total_passed + self.total_failed + self.total_skipped

    @property
    def success_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return self.total_passed / self.total_tests * 100


# Enterprise test modules and their associated tickets
ENTERPRISE_TESTS = [
    # TRACE-001: Simulation Mode
    {
        "ticket": "TRACE-001",
        "name": "Simulation Mode",
        "modules": [
            "packages.core.simulation.tests.test_simulation",
            "packages.core.simulation.tests.test_trace_v1",
        ],
        "required_tests": [
            "test_simulation_never_calls_tools",
            "test_simulation_trace_is_deterministic_for_same_input",
            "test_golden_traces",
            "test_trace_deterministic_across_100_runs",
            "test_null_tool_executor_blocks_all_tools",
            "test_tool_call_blocked_step_logged",
        ],
    },
    # TENANT-001: Multi-Tenant at Scale
    {
        "ticket": "TENANT-001",
        "name": "Multi-Tenant Isolation",
        "modules": [
            "packages.core.multitenancy.tests.test_isolation",
            "packages.core.multitenancy.tests.test_rls",
        ],
        "required_tests": [
            "test_cross_tenant_read_is_blocked",
            "test_cross_tenant_read_blocked_without_where",
            "test_cross_tenant_write_blocked",
            "test_end_to_end_api_propagation",
            "test_tenant_context_propagation",
            "test_isolation_levels",
        ],
    },
    # ONBOARD-001: Auto-Onboarding
    {
        "ticket": "ONBOARD-001",
        "name": "Auto-Onboarding",
        "modules": [
            "packages.onboarding.tests.test_onboarding",
            "packages.onboarding.tests.test_deployment",
        ],
        "required_tests": [
            "test_approve_and_deploy_creates_deployment_package",
            "test_preview_returns_confidence_scores",
            "test_checklist_approval_workflow",
            "test_preview_returns_package_hash_and_checksums",
            "test_approve_and_deploy_creates_deployment_structure",
            "test_hitl_approvals_enforced_via_confidence",
            "test_replay_deployment_produces_identical_state",
        ],
    },
]


def run_pytest_module(module: str) -> tuple[int, int, int, list[str], float]:
    """Run pytest on a specific module.

    Returns:
        Tuple of (passed, failed, skipped, errors, duration)
    """
    start_time = time.time()

    try:
        # Run pytest with verbose output
        result = subprocess.run(
            [
                sys.executable, "-m", "pytest",
                "-v",
                "--tb=short",
                "-q",
                module.replace(".", "/") + ".py",
            ],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        duration = time.time() - start_time
        output = result.stdout + result.stderr

        # Parse results
        passed = 0
        failed = 0
        skipped = 0
        errors = []

        # Look for pytest summary line like "20 passed in 0.14s" or "1 failed, 19 passed"
        for line in output.split("\n"):
            # Match patterns like "20 passed", "1 failed", "3 skipped"
            passed_match = re.search(r"(\d+) passed", line)
            failed_match = re.search(r"(\d+) failed", line)
            skipped_match = re.search(r"(\d+) skipped", line)

            if passed_match:
                passed = max(passed, int(passed_match.group(1)))
            if failed_match:
                failed = max(failed, int(failed_match.group(1)))
            if skipped_match:
                skipped = max(skipped, int(skipped_match.group(1)))

            # Capture error messages
            if "FAILED" in line or "ERROR" in line:
                errors.append(line.strip())

        return passed, failed, skipped, errors, duration

    except subprocess.TimeoutExpired:
        return 0, 1, 0, ["Test timeout exceeded"], time.time() - start_time
    except Exception as e:
        return 0, 1, 0, [str(e)], time.time() - start_time


def print_header() -> None:
    """Print certification header."""
    print("=" * 80)
    print()
    print("    HAAIS aiOS - Enterprise Certification Suite")
    print()
    print("=" * 80)
    print()


def print_ticket_header(ticket: str, name: str) -> None:
    """Print ticket section header."""
    print(f"\n{'-' * 80}")
    print(f"  {ticket}: {name}")
    print(f"{'-' * 80}")


def print_module_result(module: str, result: TestResult) -> None:
    """Print module test results."""
    status = "[PASS]" if result.failed == 0 else "[FAIL]"
    color_start = "\033[92m" if result.failed == 0 else "\033[91m"
    color_end = "\033[0m"

    print(f"  {color_start}{status}{color_end} {module}")
    print(f"      Passed: {result.passed} | Failed: {result.failed} | Skipped: {result.skipped}")
    print(f"      Duration: {result.duration_seconds:.2f}s")

    if result.errors:
        for error in result.errors[:3]:  # Show first 3 errors
            print(f"      [X] {error[:70]}...")


def print_summary(report: CertificationReport) -> None:
    """Print certification summary."""
    print("\n" + "=" * 80)
    print("                         CERTIFICATION SUMMARY")
    print("=" * 80)

    print(f"\n  Timestamp: {report.timestamp}")
    print(f"  Total Duration: {report.total_duration:.2f}s")
    print()

    # Results table
    print("  +--------------+---------+---------+---------+-------------+")
    print("  |    Ticket    | Passed  | Failed  | Skipped |   Status    |")
    print("  +--------------+---------+---------+---------+-------------+")

    for test_config in ENTERPRISE_TESTS:
        ticket = test_config["ticket"]
        ticket_results = [r for r in report.results if r.ticket == ticket]

        passed = sum(r.passed for r in ticket_results)
        failed = sum(r.failed for r in ticket_results)
        skipped = sum(r.skipped for r in ticket_results)

        status = "PASS" if failed == 0 else "FAIL"
        color = "\033[92m" if failed == 0 else "\033[91m"
        end_color = "\033[0m"

        print(f"  | {ticket:12} | {passed:7} | {failed:7} | {skipped:7} | {color}{status:11}{end_color} |")

    print("  +--------------+---------+---------+---------+-------------+")

    # Overall totals
    print(f"\n  Total Tests: {report.total_tests}")
    print(f"  Passed: {report.total_passed} ({report.success_rate:.1f}%)")
    print(f"  Failed: {report.total_failed}")
    print(f"  Skipped: {report.total_skipped}")

    # Certification status
    print("\n" + "-" * 80)
    if report.certified:
        print("\n  ************************************************************")
        print("  *                                                          *")
        print("  *             \033[92mENTERPRISE CERTIFIED\033[0m                         *")
        print("  *                                                          *")
        print("  ************************************************************")
        print("\n  All enterprise requirements met. System is ready for production.")
    else:
        print("\n  ************************************************************")
        print("  *                                                          *")
        print("  *             \033[91mCERTIFICATION FAILED\033[0m                          *")
        print("  *                                                          *")
        print("  ************************************************************")
        print("\n  The following tickets have failing tests:")
        for test_config in ENTERPRISE_TESTS:
            ticket = test_config["ticket"]
            ticket_results = [r for r in report.results if r.ticket == ticket]
            failed = sum(r.failed for r in ticket_results)
            if failed > 0:
                print(f"    - {ticket}: {test_config['name']} ({failed} failures)")

    print("\n" + "=" * 80)


def main() -> int:
    """Run enterprise certification and print report."""
    print_header()

    report = CertificationReport(
        timestamp=datetime.now(UTC).isoformat()
    )

    # Run tests for each ticket
    for test_config in ENTERPRISE_TESTS:
        ticket = test_config["ticket"]
        name = test_config["name"]

        print_ticket_header(ticket, name)

        for module in test_config["modules"]:
            print(f"\n  Running: {module}...")

            passed, failed, skipped, errors, duration = run_pytest_module(module)

            result = TestResult(
                module=module,
                ticket=ticket,
                passed=passed,
                failed=failed,
                skipped=skipped,
                errors=errors,
                duration_seconds=duration,
            )

            report.add_result(result)
            print_module_result(module, result)

    # Determine certification status
    report.certified = report.total_failed == 0 and report.total_passed > 0

    # Print summary
    print_summary(report)

    # Return exit code
    return 0 if report.certified else 1


if __name__ == "__main__":
    sys.exit(main())

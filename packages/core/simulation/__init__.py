"""Simulation module for dry-run policy testing."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from packages.core.concierge import classify_intent, detect_risks
from packages.core.governance import PolicySet, evaluate_governance
from packages.core.schemas.models import (
    GovernanceDecision,
    Intent,
    RiskSignals,
    UserContext,
)

AGENT_MAP = {
    "Comms": "communications_agent",
    "Legal": "legal_agent",
    "HR": "hr_agent",
    "Finance": "finance_agent",
    "General": "research_agent",
}


class SimulationResult(BaseModel):
    """Result of a single simulation."""

    intent: Intent
    risk: RiskSignals
    governance: GovernanceDecision
    agent_id: str
    audit_event_stub: dict[str, Any]


class BatchSimulationResult(BaseModel):
    """Result of a batch simulation."""

    total: int
    results: list[SimulationResult]
    tools_executed: int = Field(default=0)


class SimulationRunner:
    """Run simulations without executing tools."""

    def __init__(self, policy_set: PolicySet) -> None:
        self.policy_set = policy_set

    def simulate_single(
        self,
        text: str,
        tenant_id: str,
        user_id: str = "anonymous",
        department: str = "General",
        role: str = "employee",
    ) -> SimulationResult:
        """Simulate a single request."""
        intent = classify_intent(text)
        risk = detect_risks(text)

        ctx = UserContext(
            tenant_id=tenant_id,
            user_id=user_id,
            role=role,
            department=department,
        )

        governance = evaluate_governance(intent, risk, ctx, self.policy_set)
        agent_id = AGENT_MAP.get(intent.domain, "research_agent")

        audit_stub = {
            "request_id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "user_id": user_id,
            "department": department,
            "timestamp": datetime.now(UTC).isoformat(),
            "request_text": text,
            "intent": {
                "domain": intent.domain,
                "task": intent.task,
                "audience": intent.audience,
                "impact": intent.impact,
                "confidence": intent.confidence,
            },
            "risk_signals": risk.signals,
            "governance": {
                "hitl_mode": governance.hitl_mode.value,
                "tools_allowed": governance.tools_allowed,
                "approval_required": governance.approval_required,
                "policy_trigger_ids": governance.policy_trigger_ids,
            },
            "agent_id": agent_id,
            "simulation_mode": True,
            "tools_executed": [],
        }

        return SimulationResult(
            intent=intent,
            risk=risk,
            governance=governance,
            agent_id=agent_id,
            audit_event_stub=audit_stub,
        )

    def simulate_batch(
        self,
        inputs: list[dict[str, Any]],
        tenant_id: str,
    ) -> BatchSimulationResult:
        """Simulate a batch of requests."""
        results = []
        for inp in inputs:
            result = self.simulate_single(
                text=inp.get("text", ""),
                tenant_id=tenant_id,
                user_id=inp.get("user_id", "anonymous"),
                department=inp.get("department", "General"),
            )
            results.append(result)

        return BatchSimulationResult(
            total=len(results),
            results=results,
            tools_executed=0,
        )


def simulate_batch(
    inputs: list[dict[str, Any]],
    tenant_id: str,
    policy_set: PolicySet,
) -> BatchSimulationResult:
    """Convenience function for batch simulation."""
    runner = SimulationRunner(policy_set=policy_set)
    return runner.simulate_batch(inputs=inputs, tenant_id=tenant_id)


__all__ = [
    "BatchSimulationResult",
    "SimulationResult",
    "SimulationRunner",
    "simulate_batch",
]

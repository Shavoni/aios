"""Deterministic Simulation Runner.

Provides:
- NullToolExecutor that raises if tools called and logs tool_call_blocked
- SimulationRunner for deterministic execution
- Rule-based stub responses
- Integration with DecisionTraceV1 schema
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Callable
from enum import Enum

from .tracer import ExecutionTracer, TraceEventType, ExecutionTrace
from .schema import (
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


class SimulationError(Exception):
    """Error during simulation execution."""
    pass


class ToolCallAttemptedError(SimulationError):
    """Raised when a tool is called during simulation mode."""

    def __init__(self, tool_name: str, args: dict[str, Any]):
        self.tool_name = tool_name
        self.args = args
        super().__init__(
            f"Tool '{tool_name}' was called during simulation mode. "
            f"Simulation must be deterministic and cannot execute real tools."
        )


class NullToolExecutor:
    """Tool executor that raises if any tool is called.

    Used in simulation mode to ensure no real tools are executed.
    This guarantees deterministic behavior.

    TRACE-001: Logs tool_call_blocked trace step for each blocked tool.
    """

    def __init__(self, strict: bool = True, trace: DecisionTraceV1 | None = None):
        self._strict = strict
        self._attempted_calls: list[tuple[str, dict]] = []
        self._blocked_tools: list[ToolCallBlockedV1] = []
        self._trace = trace

    def execute(self, tool_name: str, args: dict[str, Any]) -> Any:
        """Attempt to execute a tool - raises in strict mode.

        Always logs the blocked tool call to the trace.
        """
        self._attempted_calls.append((tool_name, args))

        # Create blocked tool record
        blocked = ToolCallBlockedV1(
            tool_name=tool_name,
            arguments=args.copy(),
            blocked_at=datetime.now(UTC).isoformat(),
            reason="Simulation mode - tools disabled",
        )
        self._blocked_tools.append(blocked)

        # Add to trace if available
        if self._trace:
            self._trace.blocked_tools.append(blocked)
            # Add trace step
            step = TraceStepV1(
                step_id=str(uuid.uuid4()),
                step_type=TraceStepType.TOOL_CALL_BLOCKED,
                timestamp=datetime.now(UTC).isoformat(),
                input_data={"tool_name": tool_name, "arguments": args},
                output_data={"blocked": True, "reason": blocked.reason},
                blocked_tool=blocked,
            )
            self._trace.steps.append(step)

        if self._strict:
            raise ToolCallAttemptedError(tool_name, args)

        # In non-strict mode, return a placeholder
        return {"simulated": True, "tool": tool_name, "args": args, "blocked": True}

    def get_attempted_calls(self) -> list[tuple[str, dict]]:
        """Get list of attempted tool calls."""
        return self._attempted_calls.copy()

    def get_blocked_tools(self) -> list[ToolCallBlockedV1]:
        """Get list of blocked tool records."""
        return self._blocked_tools.copy()

    def clear(self) -> None:
        """Clear attempted calls and blocked tools."""
        self._attempted_calls.clear()
        self._blocked_tools.clear()

    def set_trace(self, trace: DecisionTraceV1) -> None:
        """Set the trace to log blocked tools to."""
        self._trace = trace


@dataclass
class DecisionTrace:
    """Complete trace of a routing decision.

    Captures all decision points during request processing
    for deterministic replay and verification.
    """

    # Request info
    request_id: str
    request_text: str
    tenant_id: str
    user_id: str

    # Timing
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    # Intent classification
    detected_intent: str = ""
    intent_confidence: float = 0.0
    intent_alternatives: list[dict[str, Any]] = field(default_factory=list)

    # Risk assessment
    risk_level: str = "low"
    risk_score: float = 0.0
    risk_factors: list[str] = field(default_factory=list)

    # Agent routing
    selected_agent: str = ""
    agent_confidence: float = 0.0
    agent_alternatives: list[dict[str, Any]] = field(default_factory=list)
    routing_reason: str = ""

    # Governance
    requires_hitl: bool = False
    hitl_reason: str = ""
    governance_checks: list[dict[str, Any]] = field(default_factory=list)

    # Model selection
    selected_model: str = ""
    model_tier: str = ""
    estimated_cost: float = 0.0

    # Knowledge base
    kb_queries: list[str] = field(default_factory=list)
    kb_results: list[dict[str, Any]] = field(default_factory=list)

    # Final response (simulated)
    response_text: str = ""
    response_type: str = ""

    # Deterministic hash
    decision_hash: str = ""

    def __post_init__(self):
        if not self.decision_hash:
            self.decision_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """Compute deterministic hash of all decision points."""
        content = json.dumps({
            "request_text": self.request_text,
            "detected_intent": self.detected_intent,
            "risk_level": self.risk_level,
            "selected_agent": self.selected_agent,
            "requires_hitl": self.requires_hitl,
            "selected_model": self.selected_model,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "request_text": self.request_text,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp,
            "detected_intent": self.detected_intent,
            "intent_confidence": self.intent_confidence,
            "intent_alternatives": self.intent_alternatives,
            "risk_level": self.risk_level,
            "risk_score": self.risk_score,
            "risk_factors": self.risk_factors,
            "selected_agent": self.selected_agent,
            "agent_confidence": self.agent_confidence,
            "agent_alternatives": self.agent_alternatives,
            "routing_reason": self.routing_reason,
            "requires_hitl": self.requires_hitl,
            "hitl_reason": self.hitl_reason,
            "governance_checks": self.governance_checks,
            "selected_model": self.selected_model,
            "model_tier": self.model_tier,
            "estimated_cost": self.estimated_cost,
            "kb_queries": self.kb_queries,
            "kb_results": self.kb_results,
            "response_text": self.response_text,
            "response_type": self.response_type,
            "decision_hash": self.decision_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DecisionTrace:
        return cls(**data)


class StubResponseGenerator:
    """Generates deterministic stub responses based on rules.

    Uses pattern matching and heuristics to generate
    predictable responses without calling LLMs.
    """

    def __init__(self):
        self._rules: list[tuple[Callable[[str], bool], str, str]] = []
        self._setup_default_rules()

    def _setup_default_rules(self) -> None:
        """Set up default response rules."""
        # HR queries
        self.add_rule(
            lambda q: any(w in q.lower() for w in ["fmla", "leave", "pto", "vacation"]),
            "hr_leave",
            "For leave requests, please submit through the HR portal. "
            "FMLA requires 30 days advance notice when foreseeable."
        )

        # Benefits queries
        self.add_rule(
            lambda q: any(w in q.lower() for w in ["benefits", "insurance", "401k", "retirement"]),
            "hr_benefits",
            "Benefits information is available in the Employee Benefits Guide. "
            "Open enrollment period is typically in November."
        )

        # IT support
        self.add_rule(
            lambda q: any(w in q.lower() for w in ["password", "login", "access", "vpn"]),
            "it_support",
            "For access issues, please contact IT Help Desk at ext. 4357 "
            "or submit a ticket through ServiceNow."
        )

        # Finance queries
        self.add_rule(
            lambda q: any(w in q.lower() for w in ["expense", "reimbursement", "budget", "invoice"]),
            "finance",
            "Expense reports must be submitted within 30 days of the expense. "
            "Please use the Concur system for all reimbursements."
        )

        # Legal queries
        self.add_rule(
            lambda q: any(w in q.lower() for w in ["contract", "legal", "nda", "agreement"]),
            "legal",
            "Legal document requests require department head approval. "
            "Standard turnaround is 5-7 business days."
        )

        # Building/Permits (municipal)
        self.add_rule(
            lambda q: any(w in q.lower() for w in ["permit", "building", "inspection", "zoning"]),
            "building",
            "Building permits can be applied for online at the Building Department portal. "
            "Typical processing time is 2-4 weeks."
        )

        # Default
        self.add_rule(
            lambda q: True,
            "general",
            "I understand your question. Let me connect you with the appropriate specialist "
            "who can provide detailed assistance."
        )

    def add_rule(
        self,
        matcher: Callable[[str], bool],
        response_type: str,
        response: str,
    ) -> None:
        """Add a response rule."""
        self._rules.append((matcher, response_type, response))

    def generate(self, query: str) -> tuple[str, str]:
        """Generate a deterministic response for a query.

        Returns:
            Tuple of (response_type, response_text)
        """
        for matcher, response_type, response in self._rules:
            if matcher(query):
                return response_type, response

        return "unknown", "I'm unable to process this request at this time."


class IntentClassifier:
    """Rule-based intent classifier for simulation.

    Provides deterministic intent classification without LLM calls.
    """

    INTENT_PATTERNS = {
        "hr_leave": ["fmla", "leave", "pto", "vacation", "sick day", "time off"],
        "hr_benefits": ["benefits", "insurance", "health", "dental", "vision", "401k", "retirement"],
        "hr_policy": ["policy", "handbook", "dress code", "remote work"],
        "hr_onboarding": ["new hire", "onboarding", "first day", "orientation"],
        "it_support": ["password", "login", "computer", "laptop", "vpn", "access"],
        "it_software": ["install", "software", "application", "license"],
        "finance_expense": ["expense", "reimbursement", "receipt"],
        "finance_budget": ["budget", "funding", "allocation"],
        "finance_invoice": ["invoice", "payment", "vendor"],
        "legal_contract": ["contract", "agreement", "nda", "terms"],
        "legal_compliance": ["compliance", "regulation", "audit"],
        "building_permit": ["permit", "building permit", "construction"],
        "building_inspection": ["inspection", "code", "violation"],
        "public_safety": ["police", "fire", "emergency", "safety"],
        "general_inquiry": ["help", "question", "information", "how do i"],
    }

    def classify(self, text: str) -> tuple[str, float, list[dict[str, Any]]]:
        """Classify intent from text.

        Returns:
            Tuple of (primary_intent, confidence, alternatives)
        """
        text_lower = text.lower()
        scores: dict[str, int] = {}

        for intent, patterns in self.INTENT_PATTERNS.items():
            score = sum(1 for p in patterns if p in text_lower)
            if score > 0:
                scores[intent] = score

        if not scores:
            return "general_inquiry", 0.5, []

        # Sort by score
        sorted_intents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary = sorted_intents[0]

        # Calculate confidence based on score and uniqueness
        max_score = primary[1]
        total_score = sum(scores.values())
        confidence = min(0.95, 0.5 + (max_score / total_score) * 0.4)

        # Build alternatives
        alternatives = [
            {"intent": intent, "confidence": score / total_score}
            for intent, score in sorted_intents[1:4]
        ]

        return primary[0], confidence, alternatives


class RiskAssessor:
    """Rule-based risk assessment for simulation."""

    HIGH_RISK_PATTERNS = [
        "terminate", "fire", "lawsuit", "legal action",
        "confidential", "secret", "classified",
        "financial", "budget cut", "layoff",
        "security breach", "data leak",
    ]

    MEDIUM_RISK_PATTERNS = [
        "contract", "agreement", "policy change",
        "personnel", "employee record",
        "vendor", "procurement",
    ]

    def assess(self, text: str) -> tuple[str, float, list[str]]:
        """Assess risk level of a request.

        Returns:
            Tuple of (risk_level, risk_score, risk_factors)
        """
        text_lower = text.lower()
        factors = []

        # Check high risk
        high_matches = [p for p in self.HIGH_RISK_PATTERNS if p in text_lower]
        if high_matches:
            factors.extend([f"high_risk_keyword:{m}" for m in high_matches])

        # Check medium risk
        medium_matches = [p for p in self.MEDIUM_RISK_PATTERNS if p in text_lower]
        if medium_matches:
            factors.extend([f"medium_risk_keyword:{m}" for m in medium_matches])

        # Calculate score
        score = len(high_matches) * 0.3 + len(medium_matches) * 0.15
        score = min(1.0, score)

        # Determine level
        if score >= 0.6:
            level = "high"
        elif score >= 0.3:
            level = "medium"
        else:
            level = "low"

        return level, score, factors


class AgentRouter:
    """Rule-based agent routing for simulation."""

    AGENT_INTENTS = {
        "hr_specialist": ["hr_leave", "hr_benefits", "hr_policy", "hr_onboarding"],
        "it_support": ["it_support", "it_software"],
        "finance_specialist": ["finance_expense", "finance_budget", "finance_invoice"],
        "legal_advisor": ["legal_contract", "legal_compliance"],
        "building_department": ["building_permit", "building_inspection"],
        "public_safety": ["public_safety"],
        "concierge": ["general_inquiry"],
    }

    def route(self, intent: str) -> tuple[str, float, list[dict[str, Any]], str]:
        """Route to an agent based on intent.

        Returns:
            Tuple of (agent, confidence, alternatives, reason)
        """
        for agent, intents in self.AGENT_INTENTS.items():
            if intent in intents:
                # Calculate confidence based on match specificity
                confidence = 0.95 if len(intents) == 1 else 0.85

                # Build alternatives
                alternatives = [
                    {"agent": a, "confidence": 0.3}
                    for a in ["concierge"]
                    if a != agent
                ]

                reason = f"Intent '{intent}' maps to {agent}"
                return agent, confidence, alternatives, reason

        return "concierge", 0.7, [], "No specific agent match, using concierge"


class ModelSelector:
    """Rule-based model selection for simulation."""

    def select(
        self,
        intent: str,
        risk_level: str,
        requires_hitl: bool,
    ) -> tuple[str, str, float]:
        """Select appropriate model tier.

        Returns:
            Tuple of (model_name, tier, estimated_cost)
        """
        if risk_level == "high" or requires_hitl:
            return "claude-opus-4", "premium", 0.015
        elif risk_level == "medium":
            return "gpt-4o", "standard", 0.003
        else:
            return "gpt-4o-mini", "economy", 0.0001


class SimulationRunner:
    """Runs deterministic simulations of request processing.

    Executes the full routing pipeline without calling real tools or LLMs.
    Produces DecisionTrace objects for verification and testing.
    """

    def __init__(self):
        self._tool_executor = NullToolExecutor(strict=True)
        self._intent_classifier = IntentClassifier()
        self._risk_assessor = RiskAssessor()
        self._agent_router = AgentRouter()
        self._model_selector = ModelSelector()
        self._response_generator = StubResponseGenerator()
        self._tracer: ExecutionTracer | None = None

    def run(
        self,
        request_text: str,
        tenant_id: str = "default",
        user_id: str = "anonymous",
        request_id: str | None = None,
    ) -> DecisionTrace:
        """Run a simulation and return the decision trace.

        This method is fully deterministic - the same input will
        always produce the same output.
        """
        import uuid
        req_id = request_id or str(uuid.uuid4())

        # Create tracer for detailed logging
        self._tracer = ExecutionTracer(
            trace_id=req_id,
            tenant_id=tenant_id,
            user_id=user_id,
            request_text=request_text,
            is_simulation=True,
        )

        # Initialize decision trace
        trace = DecisionTrace(
            request_id=req_id,
            request_text=request_text,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        # Step 1: Intent Classification
        with self._tracer.event(TraceEventType.INTENT_CLASSIFICATION, {"text": request_text}):
            intent, confidence, alternatives = self._intent_classifier.classify(request_text)
            trace.detected_intent = intent
            trace.intent_confidence = confidence
            trace.intent_alternatives = alternatives

        # Step 2: Risk Assessment
        with self._tracer.event(TraceEventType.RISK_DETECTION, {"intent": intent}):
            risk_level, risk_score, risk_factors = self._risk_assessor.assess(request_text)
            trace.risk_level = risk_level
            trace.risk_score = risk_score
            trace.risk_factors = risk_factors

        # Step 3: Governance Check
        with self._tracer.event(TraceEventType.GOVERNANCE_CHECK, {"risk_level": risk_level}):
            requires_hitl = risk_level in ("high", "medium")
            hitl_reason = ""
            if requires_hitl:
                hitl_reason = f"Risk level {risk_level} requires human review"
            trace.requires_hitl = requires_hitl
            trace.hitl_reason = hitl_reason
            trace.governance_checks = [
                {"check": "risk_threshold", "passed": risk_level == "low"},
                {"check": "hitl_required", "result": requires_hitl},
            ]

        # Step 4: Agent Routing
        with self._tracer.event(TraceEventType.AGENT_ROUTING, {"intent": intent}):
            agent, agent_conf, agent_alts, reason = self._agent_router.route(intent)
            trace.selected_agent = agent
            trace.agent_confidence = agent_conf
            trace.agent_alternatives = agent_alts
            trace.routing_reason = reason

        # Step 5: Model Selection
        model, tier, cost = self._model_selector.select(intent, risk_level, requires_hitl)
        trace.selected_model = model
        trace.model_tier = tier
        trace.estimated_cost = cost

        # Step 6: Generate Response
        response_type, response_text = self._response_generator.generate(request_text)
        trace.response_type = response_type
        trace.response_text = response_text

        # Compute final hash
        trace.decision_hash = trace._compute_hash()

        # Finish tracer
        self._tracer.finish(
            response=response_text,
            success=True,
        )

        return trace

    def get_execution_trace(self) -> ExecutionTrace | None:
        """Get the detailed execution trace from the last run."""
        if self._tracer:
            return self._tracer.trace
        return None

    def verify_determinism(
        self,
        request_text: str,
        runs: int = 3,
    ) -> tuple[bool, list[str]]:
        """Verify that simulation is deterministic.

        Runs the same request multiple times and checks
        that all decision hashes match.

        Returns:
            Tuple of (is_deterministic, list_of_hashes)
        """
        hashes = []
        for _ in range(runs):
            trace = self.run(request_text)
            hashes.append(trace.decision_hash)

        is_deterministic = len(set(hashes)) == 1
        return is_deterministic, hashes

    def run_v1(
        self,
        request_text: str,
        tenant_id: str = "default",
        user_id: str = "anonymous",
        trace_id: str | None = None,
        request_id: str | None = None,
    ) -> DecisionTraceV1:
        """Run a simulation and return the strict schema trace.

        TRACE-001: Uses DecisionTraceV1 with canonical JSON and deterministic hash.
        Timestamps are excluded from the hash computation.
        """
        trace_id = trace_id or str(uuid.uuid4())
        request_id = request_id or str(uuid.uuid4())

        # Create V1 trace
        trace = create_trace(
            request_text=request_text,
            tenant_id=tenant_id,
            user_id=user_id,
            trace_id=trace_id,
            request_id=request_id,
        )

        # Set up tool executor to log to this trace
        self._tool_executor = NullToolExecutor(strict=True, trace=trace)

        # Step 1: Intent Classification
        intent, confidence, alternatives = self._intent_classifier.classify(request_text)
        trace.intent = IntentResultV1(
            primary_intent=intent,
            confidence=ConfidenceScoreV1(
                score=round(confidence, 6),
                level="high" if confidence >= 0.85 else "medium" if confidence >= 0.6 else "low" if confidence >= 0.4 else "very_low",
                reason="Rule-based classification",
                evidence=[f"Matched patterns for {intent}"],
            ),
            alternatives=alternatives,
        )
        trace.steps.append(TraceStepV1(
            step_id=str(uuid.uuid4()),
            step_type=TraceStepType.INTENT_CLASSIFICATION,
            timestamp=datetime.now(UTC).isoformat(),
            input_data={"text": request_text[:200]},
            output_data={"intent": intent, "confidence": round(confidence, 6)},
        ))

        # Step 2: Risk Assessment
        risk_level, risk_score, risk_factors = self._risk_assessor.assess(request_text)
        trace.risk = RiskResultV1(
            level=risk_level,
            score=round(risk_score, 6),
            factors=risk_factors,
        )
        trace.steps.append(TraceStepV1(
            step_id=str(uuid.uuid4()),
            step_type=TraceStepType.RISK_ASSESSMENT,
            timestamp=datetime.now(UTC).isoformat(),
            input_data={"intent": intent},
            output_data={"level": risk_level, "score": round(risk_score, 6)},
        ))

        # Step 3: Governance Check
        requires_hitl = risk_level in ("high", "medium")
        hitl_reason = f"Risk level {risk_level} requires human review" if requires_hitl else ""
        trace.governance = GovernanceResultV1(
            requires_hitl=requires_hitl,
            hitl_reason=hitl_reason,
            checks_passed=["syntax_valid"] if not requires_hitl else [],
            checks_failed=["risk_threshold"] if requires_hitl else [],
            policy_ids=["default_governance"],
        )
        trace.steps.append(TraceStepV1(
            step_id=str(uuid.uuid4()),
            step_type=TraceStepType.GOVERNANCE_CHECK,
            timestamp=datetime.now(UTC).isoformat(),
            input_data={"risk_level": risk_level},
            output_data={"requires_hitl": requires_hitl},
        ))

        # Step 4: Agent Routing
        agent, agent_conf, agent_alts, reason = self._agent_router.route(intent)
        trace.routing = RoutingResultV1(
            selected_agent=agent,
            confidence=ConfidenceScoreV1(
                score=round(agent_conf, 6),
                level="high" if agent_conf >= 0.85 else "medium",
                reason=reason,
            ),
            alternatives=agent_alts,
            routing_reason=reason,
        )
        trace.steps.append(TraceStepV1(
            step_id=str(uuid.uuid4()),
            step_type=TraceStepType.AGENT_ROUTING,
            timestamp=datetime.now(UTC).isoformat(),
            input_data={"intent": intent},
            output_data={"agent": agent, "confidence": round(agent_conf, 6)},
        ))

        # Step 5: Model Selection
        model, tier, cost = self._model_selector.select(intent, risk_level, requires_hitl)
        trace.model_selection = ModelSelectionV1(
            model_id=model,
            tier=tier,
            estimated_cost_usd=round(cost, 6),
        )

        # Step 6: Generate Response
        response_type, response_text = self._response_generator.generate(request_text)
        trace.response_type = response_type
        trace.response_text = response_text
        trace.steps.append(TraceStepV1(
            step_id=str(uuid.uuid4()),
            step_type=TraceStepType.RESPONSE_GENERATION,
            timestamp=datetime.now(UTC).isoformat(),
            input_data={"agent": agent, "model": model},
            output_data={"response_type": response_type},
        ))

        # Finalize
        trace.completed_at = datetime.now(UTC).isoformat()
        trace.success = True
        trace.finalize()

        return trace

    def verify_determinism_v1(
        self,
        request_text: str,
        runs: int = 100,
        tenant_id: str = "test-tenant",
    ) -> tuple[bool, list[str]]:
        """Verify that V1 simulation is deterministic across many runs.

        TRACE-001: test_trace_deterministic_across_100_runs
        """
        hashes = []
        for _ in range(runs):
            trace = self.run_v1(request_text, tenant_id=tenant_id)
            hashes.append(trace.trace_hash)

        is_deterministic = len(set(hashes)) == 1
        return is_deterministic, hashes


__all__ = [
    "SimulationError",
    "ToolCallAttemptedError",
    "NullToolExecutor",
    "DecisionTrace",
    "StubResponseGenerator",
    "IntentClassifier",
    "RiskAssessor",
    "AgentRouter",
    "ModelSelector",
    "SimulationRunner",
    # Schema types
    "TRACE_VERSION",
    "DecisionTraceV1",
    "TraceStepV1",
    "TraceStepType",
    "ConfidenceScoreV1",
    "IntentResultV1",
    "RiskResultV1",
    "GovernanceResultV1",
    "RoutingResultV1",
    "ModelSelectionV1",
    "ToolCallBlockedV1",
    "create_trace",
]

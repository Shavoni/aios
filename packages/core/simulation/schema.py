"""Strict Pydantic Schema for Decision Traces.

TRACE-001 Acceptance Criteria:
1) Strict Pydantic trace schema (DecisionTraceV1) + trace_version
2) Canonical JSON + deterministic trace_hash (sorted keys, stable floats)
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, UTC
from decimal import Decimal
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator

# Current schema version
TRACE_VERSION = "1.0.0"


class TraceStepType(str, Enum):
    """Types of trace steps."""

    REQUEST_RECEIVED = "request_received"
    INTENT_CLASSIFICATION = "intent_classification"
    RISK_ASSESSMENT = "risk_assessment"
    GOVERNANCE_CHECK = "governance_check"
    AGENT_ROUTING = "agent_routing"
    MODEL_SELECTION = "model_selection"
    KB_QUERY = "kb_query"
    TOOL_CALL_BLOCKED = "tool_call_blocked"
    RESPONSE_GENERATION = "response_generation"
    REQUEST_COMPLETE = "request_complete"
    ERROR = "error"


class ConfidenceScoreV1(BaseModel):
    """Confidence score with validation."""

    score: float = Field(..., ge=0.0, le=1.0, description="Score between 0 and 1")
    level: Literal["high", "medium", "low", "very_low"]
    reason: str = ""
    evidence: list[str] = Field(default_factory=list)

    @field_validator("score", mode="before")
    @classmethod
    def round_score(cls, v: float) -> float:
        """Round to 6 decimal places for determinism."""
        return round(float(v), 6)

    @model_validator(mode="after")
    def set_level_from_score(self) -> "ConfidenceScoreV1":
        """Ensure level matches score."""
        if self.score >= 0.85:
            object.__setattr__(self, "level", "high")
        elif self.score >= 0.60:
            object.__setattr__(self, "level", "medium")
        elif self.score >= 0.40:
            object.__setattr__(self, "level", "low")
        else:
            object.__setattr__(self, "level", "very_low")
        return self


class IntentResultV1(BaseModel):
    """Intent classification result."""

    primary_intent: str
    confidence: ConfidenceScoreV1
    alternatives: list[dict[str, Any]] = Field(default_factory=list)


class RiskResultV1(BaseModel):
    """Risk assessment result."""

    level: Literal["low", "medium", "high", "critical"]
    score: float = Field(..., ge=0.0, le=1.0)
    factors: list[str] = Field(default_factory=list)

    @field_validator("score", mode="before")
    @classmethod
    def round_score(cls, v: float) -> float:
        return round(float(v), 6)


class GovernanceResultV1(BaseModel):
    """Governance check result."""

    requires_hitl: bool
    hitl_reason: str = ""
    checks_passed: list[str] = Field(default_factory=list)
    checks_failed: list[str] = Field(default_factory=list)
    policy_ids: list[str] = Field(default_factory=list)


class RoutingResultV1(BaseModel):
    """Agent routing result."""

    selected_agent: str
    confidence: ConfidenceScoreV1
    alternatives: list[dict[str, Any]] = Field(default_factory=list)
    routing_reason: str = ""


class ModelSelectionV1(BaseModel):
    """Model selection result."""

    model_id: str
    tier: Literal["economy", "standard", "premium"]
    estimated_cost_usd: float = Field(..., ge=0.0)

    @field_validator("estimated_cost_usd", mode="before")
    @classmethod
    def round_cost(cls, v: float) -> float:
        return round(float(v), 6)


class ToolCallBlockedV1(BaseModel):
    """Record of a blocked tool call."""

    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    blocked_at: str  # ISO timestamp (excluded from hash)
    reason: str = "Simulation mode - tools disabled"


class TraceStepV1(BaseModel):
    """A single step in the execution trace."""

    step_id: str
    step_type: TraceStepType
    timestamp: str  # ISO format, excluded from hash
    duration_ms: float = Field(default=0.0, ge=0.0)

    # Step-specific data
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    # For tool_call_blocked steps
    blocked_tool: ToolCallBlockedV1 | None = None

    @field_validator("duration_ms", mode="before")
    @classmethod
    def round_duration(cls, v: float) -> float:
        return round(float(v), 3)


class DecisionTraceV1(BaseModel):
    """Complete decision trace with strict schema.

    Version 1.0.0 of the trace schema.
    """

    # Version and identification
    trace_version: Literal["1.0.0"] = TRACE_VERSION
    trace_id: str

    # Request context
    request_id: str
    request_text: str
    tenant_id: str
    user_id: str

    # Timestamps (excluded from deterministic hash)
    created_at: str  # ISO format
    completed_at: str | None = None

    # Governance policy state at time of decision
    policy_version: int = Field(default=1, description="Governance policy version at decision time")
    policy_hash: str = Field(default="", description="Hash of governance policies at decision time")

    # Classification results
    intent: IntentResultV1 | None = None
    risk: RiskResultV1 | None = None
    governance: GovernanceResultV1 | None = None
    routing: RoutingResultV1 | None = None
    model_selection: ModelSelectionV1 | None = None

    # Execution steps
    steps: list[TraceStepV1] = Field(default_factory=list)

    # Blocked tool calls
    blocked_tools: list[ToolCallBlockedV1] = Field(default_factory=list)

    # Response
    response_text: str = ""
    response_type: str = ""

    # Status
    success: bool = True
    error_message: str = ""

    # Deterministic hash (computed, not input)
    trace_hash: str = ""

    # Simulation flag
    is_simulation: bool = True

    class Config:
        frozen = False  # Allow modification for hash computation

    def compute_hash(self) -> str:
        """Compute deterministic hash from trace content.

        Excludes timestamps and other non-deterministic fields.
        Uses canonical JSON with sorted keys and stable floats.
        """
        # Build hashable content (excluding timestamps)
        hashable = {
            "trace_version": self.trace_version,
            "request_text": self.request_text,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "policy_version": self.policy_version,
            "policy_hash": self.policy_hash,
            "intent": self._serialize_for_hash(self.intent),
            "risk": self._serialize_for_hash(self.risk),
            "governance": self._serialize_for_hash(self.governance),
            "routing": self._serialize_for_hash(self.routing),
            "model_selection": self._serialize_for_hash(self.model_selection),
            "response_text": self.response_text,
            "response_type": self.response_type,
            "success": self.success,
            "blocked_tools": [
                {"tool_name": t.tool_name, "arguments": self._sort_dict(t.arguments)}
                for t in self.blocked_tools
            ],
        }

        # Canonical JSON
        canonical = self._to_canonical_json(hashable)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def _serialize_for_hash(self, obj: BaseModel | None) -> dict | None:
        """Serialize a model for hashing, excluding timestamps."""
        if obj is None:
            return None
        data = obj.model_dump()
        # Remove timestamp fields
        for key in list(data.keys()):
            if "timestamp" in key.lower() or "at" in key.lower():
                del data[key]
        return self._sort_dict(data)

    def _sort_dict(self, d: dict) -> dict:
        """Recursively sort dictionary keys."""
        result = {}
        for key in sorted(d.keys()):
            value = d[key]
            if isinstance(value, dict):
                result[key] = self._sort_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    self._sort_dict(v) if isinstance(v, dict) else v
                    for v in value
                ]
            else:
                result[key] = value
        return result

    def _to_canonical_json(self, obj: Any) -> str:
        """Convert to canonical JSON with sorted keys and stable floats."""
        return json.dumps(
            obj,
            sort_keys=True,
            separators=(",", ":"),
            default=self._json_serializer,
        )

    def _json_serializer(self, obj: Any) -> Any:
        """Custom JSON serializer for stability."""
        if isinstance(obj, float):
            # Round to 6 decimal places for determinism
            return round(obj, 6)
        if isinstance(obj, Decimal):
            return round(float(obj), 6)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Enum):
            return obj.value
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    def finalize(self) -> "DecisionTraceV1":
        """Finalize the trace by computing the hash."""
        self.trace_hash = self.compute_hash()
        return self

    def to_canonical_dict(self) -> dict[str, Any]:
        """Export to canonical dictionary format."""
        return self._sort_dict(self.model_dump())

    def to_canonical_json(self) -> str:
        """Export to canonical JSON string."""
        return self._to_canonical_json(self.to_canonical_dict())

    def to_csv_row(self) -> dict[str, Any]:
        """Export trace as a flat CSV-compatible row.

        Returns a dictionary suitable for CSV DictWriter.
        """
        return {
            "trace_id": self.trace_id,
            "trace_version": self.trace_version,
            "trace_hash": self.trace_hash,
            "request_id": self.request_id,
            "request_text": self.request_text[:500],  # Truncate for CSV
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "completed_at": self.completed_at or "",
            "policy_version": self.policy_version,
            "policy_hash": self.policy_hash,
            "intent_primary": self.intent.primary_intent if self.intent else "",
            "intent_confidence": self.intent.confidence.score if self.intent else 0.0,
            "risk_level": self.risk.level if self.risk else "",
            "risk_score": self.risk.score if self.risk else 0.0,
            "risk_factors": ";".join(self.risk.factors) if self.risk else "",
            "governance_requires_hitl": self.governance.requires_hitl if self.governance else False,
            "governance_hitl_reason": self.governance.hitl_reason if self.governance else "",
            "governance_policy_ids": ";".join(self.governance.policy_ids) if self.governance else "",
            "routing_agent": self.routing.selected_agent if self.routing else "",
            "routing_confidence": self.routing.confidence.score if self.routing else 0.0,
            "model_id": self.model_selection.model_id if self.model_selection else "",
            "model_tier": self.model_selection.tier if self.model_selection else "",
            "model_cost_usd": self.model_selection.estimated_cost_usd if self.model_selection else 0.0,
            "response_type": self.response_type,
            "response_length": len(self.response_text),
            "blocked_tools_count": len(self.blocked_tools),
            "blocked_tool_names": ";".join(t.tool_name for t in self.blocked_tools),
            "steps_count": len(self.steps),
            "success": self.success,
            "error_message": self.error_message,
            "is_simulation": self.is_simulation,
        }

    @staticmethod
    def csv_headers() -> list[str]:
        """Get CSV column headers in order."""
        return [
            "trace_id", "trace_version", "trace_hash", "request_id", "request_text",
            "tenant_id", "user_id", "created_at", "completed_at",
            "policy_version", "policy_hash",
            "intent_primary", "intent_confidence",
            "risk_level", "risk_score", "risk_factors",
            "governance_requires_hitl", "governance_hitl_reason", "governance_policy_ids",
            "routing_agent", "routing_confidence",
            "model_id", "model_tier", "model_cost_usd",
            "response_type", "response_length",
            "blocked_tools_count", "blocked_tool_names",
            "steps_count", "success", "error_message", "is_simulation",
        ]

    def to_siem_cef(self) -> str:
        """Export trace in CEF (Common Event Format) for SIEM integration.

        CEF format: CEF:Version|Device Vendor|Device Product|Device Version|Signature ID|Name|Severity|Extension
        """
        # Determine severity (0-10) based on risk level
        severity_map = {"low": 3, "medium": 5, "high": 7, "critical": 10}
        severity = severity_map.get(self.risk.level, 3) if self.risk else 3

        # Build CEF header
        cef_header = (
            f"CEF:0|HAAIS|AIOS|1.0|"
            f"{self.trace_id}|"
            f"AI Decision Trace|"
            f"{severity}|"
        )

        # Build extension (key=value pairs)
        extensions = {
            "rt": self.created_at,
            "src": self.tenant_id,
            "suser": self.user_id,
            "msg": self.request_text[:200].replace("=", "\\=").replace("|", "\\|"),
            "outcome": "Success" if self.success else "Failure",
            "cs1": self.intent.primary_intent if self.intent else "",
            "cs1Label": "Intent",
            "cs2": self.risk.level if self.risk else "",
            "cs2Label": "RiskLevel",
            "cs3": self.routing.selected_agent if self.routing else "",
            "cs3Label": "RoutedAgent",
            "cs4": str(self.governance.requires_hitl) if self.governance else "False",
            "cs4Label": "RequiresHITL",
            "cs5": self.policy_hash[:16] if self.policy_hash else "",
            "cs5Label": "PolicyHash",
            "cn1": self.policy_version,
            "cn1Label": "PolicyVersion",
            "cn2": len(self.blocked_tools),
            "cn2Label": "BlockedToolsCount",
            "cfp1": self.risk.score if self.risk else 0.0,
            "cfp1Label": "RiskScore",
        }

        # Format extension string
        ext_str = " ".join(f"{k}={v}" for k, v in extensions.items() if v)

        return cef_header + ext_str

    def to_siem_json(self) -> dict[str, Any]:
        """Export trace in JSON format optimized for SIEM ingestion.

        Includes normalized fields common across SIEM platforms.
        """
        return {
            # Standard SIEM fields
            "@timestamp": self.created_at,
            "event.kind": "event",
            "event.category": ["process"],
            "event.type": ["info"],
            "event.outcome": "success" if self.success else "failure",
            "event.id": self.trace_id,
            "event.hash": self.trace_hash,

            # Source identification
            "observer.vendor": "HAAIS",
            "observer.product": "AIOS",
            "observer.version": self.trace_version,

            # User context
            "user.id": self.user_id,
            "organization.id": self.tenant_id,

            # AI-specific fields
            "aios.request.id": self.request_id,
            "aios.request.text": self.request_text[:1000],
            "aios.response.type": self.response_type,
            "aios.response.length": len(self.response_text),

            # Policy context
            "aios.policy.version": self.policy_version,
            "aios.policy.hash": self.policy_hash,

            # Classification
            "aios.intent.primary": self.intent.primary_intent if self.intent else None,
            "aios.intent.confidence": self.intent.confidence.score if self.intent else None,

            # Risk assessment
            "aios.risk.level": self.risk.level if self.risk else None,
            "aios.risk.score": self.risk.score if self.risk else None,
            "aios.risk.factors": self.risk.factors if self.risk else [],

            # Governance
            "aios.governance.requires_hitl": self.governance.requires_hitl if self.governance else False,
            "aios.governance.hitl_reason": self.governance.hitl_reason if self.governance else None,
            "aios.governance.policy_ids": self.governance.policy_ids if self.governance else [],

            # Routing
            "aios.routing.agent": self.routing.selected_agent if self.routing else None,
            "aios.routing.confidence": self.routing.confidence.score if self.routing else None,

            # Model
            "aios.model.id": self.model_selection.model_id if self.model_selection else None,
            "aios.model.tier": self.model_selection.tier if self.model_selection else None,
            "aios.model.cost_usd": self.model_selection.estimated_cost_usd if self.model_selection else None,

            # Security
            "aios.blocked_tools": [t.tool_name for t in self.blocked_tools],
            "aios.blocked_tools_count": len(self.blocked_tools),

            # Execution
            "aios.steps_count": len(self.steps),
            "aios.is_simulation": self.is_simulation,

            # Error handling
            "error.message": self.error_message if not self.success else None,
        }


def create_trace(
    request_text: str,
    tenant_id: str,
    user_id: str = "anonymous",
    trace_id: str | None = None,
    request_id: str | None = None,
    policy_version: int = 1,
    policy_hash: str = "",
) -> DecisionTraceV1:
    """Create a new decision trace.

    Args:
        request_text: The user's request text
        tenant_id: Tenant identifier
        user_id: User identifier
        trace_id: Optional trace ID (generated if not provided)
        request_id: Optional request ID (generated if not provided)
        policy_version: Current governance policy version
        policy_hash: Hash of current governance policies
    """
    import uuid

    now = datetime.now(UTC).isoformat()
    trace_id = trace_id or str(uuid.uuid4())
    request_id = request_id or str(uuid.uuid4())

    return DecisionTraceV1(
        trace_id=trace_id,
        request_id=request_id,
        request_text=request_text,
        tenant_id=tenant_id,
        user_id=user_id,
        created_at=now,
        policy_version=policy_version,
        policy_hash=policy_hash,
    )


__all__ = [
    "TRACE_VERSION",
    "TraceStepType",
    "ConfidenceScoreV1",
    "IntentResultV1",
    "RiskResultV1",
    "GovernanceResultV1",
    "RoutingResultV1",
    "ModelSelectionV1",
    "ToolCallBlockedV1",
    "TraceStepV1",
    "DecisionTraceV1",
    "create_trace",
]

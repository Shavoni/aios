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


def create_trace(
    request_text: str,
    tenant_id: str,
    user_id: str = "anonymous",
    trace_id: str | None = None,
    request_id: str | None = None,
) -> DecisionTraceV1:
    """Create a new decision trace."""
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

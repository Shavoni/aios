"""Core data models for AIOS."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class HITLMode(str, Enum):
    """Human-in-the-loop modes."""

    INFORM = "INFORM"
    DRAFT = "DRAFT"
    ESCALATE = "ESCALATE"


class Intent(BaseModel):
    """Classified intent from user request."""

    domain: str = Field(default="General", description="Domain category")
    task: str = Field(default="unknown", description="Specific task type")
    audience: str = Field(default="internal", description="Target audience")
    impact: str = Field(default="low", description="Impact level: low, medium, high")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Classification confidence")


class RiskSignals(BaseModel):
    """Detected risk signals from user request."""

    signals: list[str] = Field(default_factory=list, description="List of risk signal codes")

    def contains(self, signal: str) -> bool:
        """Check if a specific risk signal is present."""
        return signal in self.signals


class UserContext(BaseModel):
    """User context for governance evaluation."""

    tenant_id: str = Field(description="Tenant/organization ID")
    user_id: str = Field(default="anonymous", description="User ID")
    role: str = Field(default="employee", description="User role")
    department: str = Field(default="General", description="User department")


class ProviderConstraints(BaseModel):
    """Constraints on which AI providers can be used."""

    local_only: bool = Field(default=False, description="Must use local LLM only")
    allowed_providers: list[str] = Field(default_factory=list, description="Allowed provider IDs")
    blocked_providers: list[str] = Field(default_factory=list, description="Blocked provider IDs")


class GovernanceDecision(BaseModel):
    """Result of governance policy evaluation."""

    hitl_mode: HITLMode = Field(default=HITLMode.INFORM, description="Human-in-the-loop mode")
    tools_allowed: bool = Field(default=True, description="Whether tools can be executed")
    approval_required: bool = Field(default=False, description="Whether approval is required")
    escalation_reason: str | None = Field(default=None, description="Reason for escalation")
    policy_trigger_ids: list[str] = Field(default_factory=list, description="IDs of triggered policies")
    provider_constraints: ProviderConstraints = Field(
        default_factory=ProviderConstraints, description="Provider constraints"
    )

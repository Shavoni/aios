"""AIOS Governance API."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from packages.api.config import Settings
from packages.core.concierge import classify_intent, detect_risks
from packages.core.governance import PolicyLoader, PolicySet, evaluate_governance
from packages.core.schemas.models import (
    GovernanceDecision,
    Intent,
    RiskSignals,
    UserContext,
)
from packages.core.simulation import (
    BatchSimulationResult,
    SimulationResult,
    SimulationRunner,
)

# =============================================================================
# Request Models
# =============================================================================


class ClassifyRequest(BaseModel):
    """Request for intent classification."""

    text: str = Field(..., min_length=1, description="Text to classify")


class RiskDetectionRequest(BaseModel):
    """Request for risk detection."""

    text: str = Field(..., min_length=1, description="Text to analyze for risks")


class GovernanceRequest(BaseModel):
    """Request for governance evaluation."""

    text: str = Field(..., min_length=1, description="Request text")
    tenant_id: str = Field(..., description="Tenant identifier")
    user_id: str = Field(default="anonymous", description="User identifier")
    role: str = Field(default="employee", description="User role")
    department: str = Field(default="General", description="User department")


class SimulationRequest(BaseModel):
    """Request for single simulation."""

    text: str = Field(..., min_length=1, description="Request text to simulate")
    tenant_id: str = Field(..., description="Tenant identifier")
    user_id: str = Field(default="anonymous", description="User identifier")
    department: str = Field(default="General", description="User department")
    role: str = Field(default="employee", description="User role")


class BatchSimulationRequest(BaseModel):
    """Request for batch simulation."""

    tenant_id: str = Field(..., description="Tenant identifier")
    inputs: list[dict[str, Any]] = Field(
        ...,
        min_length=1,
        description="List of inputs with 'text' and optional 'user_id', 'department'",
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    version: str = "1.0.0"
    policies_loaded: bool = False


class PolicyLoadResponse(BaseModel):
    """Response for policy load operation."""

    status: str
    message: str


# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(
    title="AIOS Governance API",
    description="AI Operating System governance framework for intent classification, "
    "risk detection, and policy evaluation.",
    version="1.0.0",
)

# Initialize state at module level for immediate availability
app.state.policy_set = PolicySet()
app.state.settings = Settings()


# =============================================================================
# Health Endpoint
# =============================================================================


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    has_policies = bool(
        app.state.policy_set.constitutional_rules
        or app.state.policy_set.organization_rules.default
        or app.state.policy_set.department_rules
    )
    return HealthResponse(
        status="ok",
        version="1.0.0",
        policies_loaded=has_policies,
    )


# =============================================================================
# Concierge Endpoints
# =============================================================================


@app.post("/classify", response_model=Intent, tags=["Concierge"])
async def classify_intent_endpoint(request: ClassifyRequest) -> Intent:
    """Classify the intent of a text input.

    Returns domain, task, audience, impact level, and confidence score.
    """
    return classify_intent(request.text)


@app.post("/risks", response_model=RiskSignals, tags=["Concierge"])
async def detect_risks_endpoint(request: RiskDetectionRequest) -> RiskSignals:
    """Detect risk signals in text.

    Returns list of risk signal codes (e.g., PII, LEGAL_CONTRACT, FINANCIAL).
    """
    return detect_risks(request.text)


# =============================================================================
# Governance Endpoints
# =============================================================================


@app.post("/governance/evaluate", response_model=GovernanceDecision, tags=["Governance"])
async def evaluate_governance_endpoint(request: GovernanceRequest) -> GovernanceDecision:
    """Evaluate governance policies for a request.

    Performs intent classification, risk detection, and policy evaluation
    to return a governance decision including HITL mode and constraints.
    """
    intent = classify_intent(request.text)
    risk = detect_risks(request.text)
    ctx = UserContext(
        tenant_id=request.tenant_id,
        user_id=request.user_id,
        role=request.role,
        department=request.department,
    )
    return evaluate_governance(intent, risk, ctx, app.state.policy_set)


@app.post("/policies", response_model=PolicyLoadResponse, tags=["Governance"])
async def load_policies(raw: dict[str, Any]) -> PolicyLoadResponse:
    """Load or replace the current policy set.

    Accepts a policy configuration dictionary with constitutional_rules,
    organization_rules, and department_rules.
    """
    try:
        loader = PolicyLoader()
        app.state.policy_set = loader.load_from_dict(raw)
        return PolicyLoadResponse(status="ok", message="Policies loaded successfully")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid policy configuration: {e}",
        ) from e


@app.get("/policies", response_model=PolicySet, tags=["Governance"])
async def get_policies() -> PolicySet:
    """Get the current policy set."""
    policy_set: PolicySet = app.state.policy_set
    return policy_set


# =============================================================================
# Simulation Endpoints
# =============================================================================


@app.post("/simulate", response_model=SimulationResult, tags=["Simulation"])
async def simulate_single(request: SimulationRequest) -> SimulationResult:
    """Simulate a single request without executing tools.

    Returns intent, risk signals, governance decision, selected agent,
    and an audit event stub for logging.
    """
    runner = SimulationRunner(policy_set=app.state.policy_set)
    return runner.simulate_single(
        text=request.text,
        tenant_id=request.tenant_id,
        user_id=request.user_id,
        department=request.department,
        role=request.role,
    )


@app.post("/simulate/batch", response_model=BatchSimulationResult, tags=["Simulation"])
async def simulate_batch_endpoint(
    request: BatchSimulationRequest,
) -> BatchSimulationResult:
    """Simulate a batch of requests.

    Processes multiple inputs and returns aggregated results.
    Useful for testing policy configurations against test cases.
    """
    runner = SimulationRunner(policy_set=app.state.policy_set)
    return runner.simulate_batch(
        inputs=request.inputs,
        tenant_id=request.tenant_id,
    )


__all__ = ["Settings", "app"]

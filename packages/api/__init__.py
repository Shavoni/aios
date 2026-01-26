"""AIOS Governance API with Enterprise Security."""

from __future__ import annotations

import os
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from packages.api.config import Settings
from packages.api.security import (
    AuthenticatedUser,
    Permission,
    Role,
    add_security_headers,
    get_current_user,
    log_audit_event,
    require_permission,
    require_role,
    validate_tenant_id,
)
from packages.core.concierge import classify_intent, detect_risks
from packages.core.governance import PolicyLoader, PolicySet, evaluate_governance
from packages.core.router import Router
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

    text: str = Field(..., min_length=1, max_length=10000, description="Text to classify")


class RiskDetectionRequest(BaseModel):
    """Request for risk detection."""

    text: str = Field(..., min_length=1, max_length=10000, description="Text to analyze for risks")


class GovernanceRequest(BaseModel):
    """Request for governance evaluation."""

    text: str = Field(..., min_length=1, max_length=10000, description="Request text")
    tenant_id: str = Field(..., min_length=1, max_length=64, description="Tenant identifier")
    user_id: str = Field(default="anonymous", max_length=64, description="User identifier")
    role: str = Field(default="employee", max_length=32, description="User role")
    department: str = Field(default="General", max_length=64, description="User department")


class SimulationRequest(BaseModel):
    """Request for single simulation."""

    text: str = Field(..., min_length=1, max_length=10000, description="Request text to simulate")
    tenant_id: str = Field(..., min_length=1, max_length=64, description="Tenant identifier")
    user_id: str = Field(default="anonymous", max_length=64, description="User identifier")
    department: str = Field(default="General", max_length=64, description="User department")
    role: str = Field(default="employee", max_length=32, description="User role")


class BatchSimulationRequest(BaseModel):
    """Request for batch simulation."""

    tenant_id: str = Field(..., min_length=1, max_length=64, description="Tenant identifier")
    inputs: list[dict[str, Any]] = Field(
        ...,
        min_length=1,
        max_length=100,  # Limit batch size
        description="List of inputs with 'text' and optional 'user_id', 'department'",
    )


class AskRequest(BaseModel):
    """Request for AI-powered response."""

    text: str = Field(..., min_length=1, max_length=10000, description="User request text")
    tenant_id: str = Field(..., min_length=1, max_length=64, description="Tenant identifier")
    user_id: str = Field(default="anonymous", max_length=64, description="User identifier")
    role: str = Field(default="employee", max_length=32, description="User role")
    department: str = Field(default="General", max_length=64, description="User department")
    use_llm_classification: bool = Field(
        default=False, description="Use LLM for intent classification (more accurate)"
    )


class AskResponse(BaseModel):
    """Response from AI assistant."""

    response: str = Field(description="AI-generated response")
    intent: Intent = Field(description="Classified intent")
    risk_signals: list[str] = Field(description="Detected risk signals")
    hitl_mode: str = Field(description="Human-in-the-loop mode applied")
    requires_approval: bool = Field(description="Whether response needs approval")
    model_used: str = Field(description="AI model used for response")
    # Note: Removed governance_triggers to avoid leaking policy IDs


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    version: str = "1.0.0"
    policies_loaded: bool = False
    llm_available: bool = False


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
    "risk detection, and policy evaluation. Enterprise-grade security enabled.",
    version="1.0.0",
    docs_url="/docs" if os.getenv("AIOS_ENV", "development") == "development" else None,
    redoc_url="/redoc" if os.getenv("AIOS_ENV", "development") == "development" else None,
)

# Security headers middleware
app.middleware("http")(add_security_headers)

# CORS middleware - restricted in production
allowed_origins = os.getenv(
    "AIOS_CORS_ORIGINS",
    "http://localhost:3000,http://localhost:3001,http://localhost:3002"
).split(",")

if os.getenv("AIOS_ENV") == "production":
    # In production, require explicit origin configuration
    if "*" in allowed_origins:
        allowed_origins = []  # Disable CORS if not properly configured

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

# Initialize state at module level for immediate availability
app.state.policy_set = PolicySet()
app.state.settings = Settings()
app.state.router = Router()

# Include agent management router
from packages.api.agents import router as agents_router
from packages.api.system import router as system_router

app.include_router(agents_router)
app.include_router(system_router)


# =============================================================================
# Health Endpoint (Public)
# =============================================================================


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Health check endpoint (no auth required)."""
    has_policies = bool(
        app.state.policy_set.constitutional_rules
        or app.state.policy_set.organization_rules.default
        or app.state.policy_set.department_rules
    )
    router: Router = app.state.router
    return HealthResponse(
        status="ok",
        version="1.0.0",
        policies_loaded=has_policies,
        llm_available=router.settings.has_api_key,
        # Note: Removed llm_provider to avoid information disclosure
    )


# =============================================================================
# Concierge Endpoints (Authenticated)
# =============================================================================


@app.post("/classify", response_model=Intent, tags=["Concierge"])
async def classify_intent_endpoint(
    request: ClassifyRequest,
    user: AuthenticatedUser = Depends(require_permission(Permission.EXECUTE_CLASSIFY)),
) -> Intent:
    """Classify the intent of a text input.

    Returns domain, task, audience, impact level, and confidence score.
    Requires EXECUTE_CLASSIFY permission.
    """
    log_audit_event(
        event_type="classify",
        user=user,
        endpoint="/classify",
        method="POST",
        action="intent_classification",
        status="success",
    )
    return classify_intent(request.text)


@app.post("/risks", response_model=RiskSignals, tags=["Concierge"])
async def detect_risks_endpoint(
    request: RiskDetectionRequest,
    user: AuthenticatedUser = Depends(require_permission(Permission.EXECUTE_CLASSIFY)),
) -> RiskSignals:
    """Detect risk signals in text.

    Returns list of risk signal codes (e.g., PII, LEGAL_CONTRACT, FINANCIAL).
    Requires EXECUTE_CLASSIFY permission.
    """
    log_audit_event(
        event_type="risk_detection",
        user=user,
        endpoint="/risks",
        method="POST",
        action="risk_analysis",
        status="success",
    )
    return detect_risks(request.text)


# =============================================================================
# Governance Endpoints (Authenticated with higher privileges)
# =============================================================================


@app.post("/governance/evaluate", response_model=GovernanceDecision, tags=["Governance"])
async def evaluate_governance_endpoint(
    request: GovernanceRequest,
    user: AuthenticatedUser = Depends(require_permission(Permission.EXECUTE_QUERY)),
) -> GovernanceDecision:
    """Evaluate governance policies for a request.

    Performs intent classification, risk detection, and policy evaluation
    to return a governance decision including HITL mode and constraints.
    Requires EXECUTE_QUERY permission.
    """
    # Validate tenant_id
    validate_tenant_id(request.tenant_id)

    intent = classify_intent(request.text)
    risk = detect_risks(request.text)
    ctx = UserContext(
        tenant_id=request.tenant_id,
        user_id=request.user_id,
        role=request.role,
        department=request.department,
    )

    result = evaluate_governance(intent, risk, ctx, app.state.policy_set)

    log_audit_event(
        event_type="governance_evaluation",
        user=user,
        endpoint="/governance/evaluate",
        method="POST",
        action="policy_evaluation",
        status="success",
        details={"hitl_mode": result.hitl_mode, "requires_approval": result.requires_approval},
    )

    return result


@app.post("/policies", response_model=PolicyLoadResponse, tags=["Governance"])
async def load_policies(
    raw: dict[str, Any],
    user: AuthenticatedUser = Depends(require_permission(Permission.WRITE_POLICIES)),
) -> PolicyLoadResponse:
    """Load or replace the current policy set.

    Accepts a policy configuration dictionary with constitutional_rules,
    organization_rules, and department_rules.
    Requires WRITE_POLICIES permission (Admin only).
    """
    try:
        loader = PolicyLoader()
        new_policy_set = loader.load_from_dict(raw)

        # Validate policy structure
        if not new_policy_set.constitutional_rules and not new_policy_set.organization_rules:
            raise ValueError("Policy set must contain at least constitutional or organization rules")

        app.state.policy_set = new_policy_set

        log_audit_event(
            event_type="policy_change",
            user=user,
            endpoint="/policies",
            method="POST",
            action="policy_load",
            status="success",
            details={
                "constitutional_rules": len(new_policy_set.constitutional_rules),
                "department_rules": len(new_policy_set.department_rules),
            },
        )

        return PolicyLoadResponse(status="ok", message="Policies loaded successfully")
    except Exception as e:
        log_audit_event(
            event_type="policy_change",
            user=user,
            endpoint="/policies",
            method="POST",
            action="policy_load",
            status="error",
            details={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid policy configuration",
        ) from e


@app.get("/policies", response_model=PolicySet, tags=["Governance"])
async def get_policies(
    user: AuthenticatedUser = Depends(require_permission(Permission.READ_POLICIES)),
) -> PolicySet:
    """Get the current policy set.

    Requires READ_POLICIES permission.
    """
    log_audit_event(
        event_type="policy_read",
        user=user,
        endpoint="/policies",
        method="GET",
        action="policy_read",
        status="success",
    )
    policy_set: PolicySet = app.state.policy_set
    return policy_set


# =============================================================================
# Simulation Endpoints (Authenticated)
# =============================================================================


@app.post("/simulate", response_model=SimulationResult, tags=["Simulation"])
async def simulate_single(
    request: SimulationRequest,
    user: AuthenticatedUser = Depends(require_permission(Permission.EXECUTE_SIMULATE)),
) -> SimulationResult:
    """Simulate a single request without executing tools.

    Returns intent, risk signals, governance decision, selected agent,
    and an audit event stub for logging.
    Requires EXECUTE_SIMULATE permission.
    """
    validate_tenant_id(request.tenant_id)

    runner = SimulationRunner(policy_set=app.state.policy_set)
    result = runner.simulate_single(
        text=request.text,
        tenant_id=request.tenant_id,
        user_id=request.user_id,
        department=request.department,
        role=request.role,
    )

    log_audit_event(
        event_type="simulation",
        user=user,
        endpoint="/simulate",
        method="POST",
        action="single_simulation",
        status="success",
    )

    return result


@app.post("/simulate/batch", response_model=BatchSimulationResult, tags=["Simulation"])
async def simulate_batch_endpoint(
    request: BatchSimulationRequest,
    user: AuthenticatedUser = Depends(require_permission(Permission.EXECUTE_SIMULATE)),
) -> BatchSimulationResult:
    """Simulate a batch of requests.

    Processes multiple inputs and returns aggregated results.
    Useful for testing policy configurations against test cases.
    Requires EXECUTE_SIMULATE permission.
    """
    validate_tenant_id(request.tenant_id)

    runner = SimulationRunner(policy_set=app.state.policy_set)
    result = runner.simulate_batch(
        inputs=request.inputs,
        tenant_id=request.tenant_id,
    )

    log_audit_event(
        event_type="simulation",
        user=user,
        endpoint="/simulate/batch",
        method="POST",
        action="batch_simulation",
        status="success",
        details={"batch_size": len(request.inputs)},
    )

    return result


# =============================================================================
# AI Assistant Endpoint (Authenticated)
# =============================================================================


@app.post("/ask", response_model=AskResponse, tags=["Assistant"])
async def ask_assistant(
    request: AskRequest,
    user: AuthenticatedUser = Depends(require_permission(Permission.EXECUTE_QUERY)),
) -> AskResponse:
    """Ask the AI assistant a question with full governance.

    This endpoint:
    1. Classifies intent (rule-based or LLM)
    2. Detects risk signals
    3. Evaluates governance policies
    4. Generates response respecting HITL mode and constraints

    Requires EXECUTE_QUERY permission.
    """
    validate_tenant_id(request.tenant_id)

    router: Router = app.state.router

    # Step 1: Classify intent
    if request.use_llm_classification and router.settings.has_anthropic_key:
        intent = router.classify_intent_with_llm(request.text)
    else:
        intent = classify_intent(request.text)

    # Step 2: Detect risks
    risk = detect_risks(request.text)

    # Step 3: Build user context
    ctx = UserContext(
        tenant_id=request.tenant_id,
        user_id=request.user_id,
        role=request.role,
        department=request.department,
    )

    # Step 4: Evaluate governance
    governance = evaluate_governance(intent, risk, ctx, app.state.policy_set)

    # Step 5: Generate response with governance constraints
    result = router.generate_response(
        request_text=request.text,
        intent=intent,
        governance=governance,
    )

    log_audit_event(
        event_type="assistant_query",
        user=user,
        endpoint="/ask",
        method="POST",
        action="ai_response",
        status="success",
        details={
            "hitl_mode": result["hitl_mode"],
            "requires_approval": result["requires_approval"],
            "model": result["model"],
        },
    )

    return AskResponse(
        response=result["text"],
        intent=intent,
        risk_signals=risk.signals,
        hitl_mode=result["hitl_mode"],
        requires_approval=result["requires_approval"],
        model_used=result["model"],
    )


__all__ = ["Settings", "app"]

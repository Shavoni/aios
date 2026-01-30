"""AIOS Governance API."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from packages.api.config import Settings
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


class AskRequest(BaseModel):
    """Request for AI-powered response."""

    text: str = Field(..., min_length=1, description="User request text")
    tenant_id: str = Field(..., description="Tenant identifier")
    user_id: str = Field(default="anonymous", description="User identifier")
    role: str = Field(default="employee", description="User role")
    department: str = Field(default="General", description="User department")
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
    governance_triggers: list[str] = Field(description="Policy IDs that triggered")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    version: str = "1.0.0"
    policies_loaded: bool = False
    llm_available: bool = False
    llm_provider: str = "none"
    # Enterprise status
    auth_mode: str = "development"
    grounding_enabled: bool = True
    audit_enabled: bool = True


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

# CORS middleware for frontend
from fastapi.middleware.cors import CORSMiddleware

# Production CORS - restrict in deployment
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:3002",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

# Tenant isolation middleware - ENTERPRISE CRITICAL
# This MUST be added after CORS but before route handlers
from packages.core.multitenancy.middleware import TenantMiddleware

app.add_middleware(
    TenantMiddleware,
    require_tenant=False,  # Set to True once all clients send X-Tenant-ID header
)

# Initialize state at module level for immediate availability
app.state.policy_set = PolicySet()
app.state.settings = Settings()
app.state.router = Router()

# Include routers
from packages.api.agents import router as agents_router
from packages.api.system import router as system_router
from packages.api.analytics import router as analytics_router
from packages.api.sessions import router as sessions_router
from packages.api.hitl import router as hitl_router
from packages.api.system_extended import router as system_extended_router
from packages.api.onboarding import router as onboarding_router
from packages.api.governance import router as governance_router
from packages.api.tenants import router as tenants_router
from packages.api.voice import router as voice_router
from packages.api.audit import router as audit_router

app.include_router(agents_router)
app.include_router(system_router)
app.include_router(analytics_router)
app.include_router(sessions_router)
app.include_router(hitl_router)
app.include_router(system_extended_router)
app.include_router(onboarding_router)
app.include_router(governance_router)
app.include_router(tenants_router)
app.include_router(voice_router)
app.include_router(audit_router)


# Startup event to start background services
@app.on_event("startup")
async def startup_event():
    """Start background services on app startup."""
    from packages.core.knowledge import start_knowledge_scheduler
    start_knowledge_scheduler()


# Shutdown event to stop background services
@app.on_event("shutdown")
async def shutdown_event():
    """Stop background services on app shutdown."""
    from packages.core.knowledge import stop_knowledge_scheduler
    stop_knowledge_scheduler()


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
    router: Router = app.state.router
    settings: Settings = app.state.settings

    return HealthResponse(
        status="ok",
        version="1.0.0",
        policies_loaded=has_policies,
        llm_available=router.settings.has_api_key,
        llm_provider=router.settings.llm_provider if router.settings.has_api_key else "none",
        # Enterprise status
        auth_mode=settings.auth_mode,
        grounding_enabled=settings.grounding_enabled,
        audit_enabled=settings.audit_enabled,
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


# =============================================================================
# AI Assistant Endpoint
# =============================================================================


@app.post("/ask", response_model=AskResponse, tags=["Assistant"])
async def ask_assistant(request: AskRequest) -> AskResponse:
    """Ask the AI assistant a question with full governance.

    This endpoint:
    1. Classifies intent (rule-based or LLM)
    2. Detects risk signals
    3. Evaluates governance policies
    4. Generates response respecting HITL mode and constraints
    """
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

    return AskResponse(
        response=result["text"],
        intent=intent,
        risk_signals=risk.signals,
        hitl_mode=result["hitl_mode"],
        requires_approval=result["requires_approval"],
        model_used=result["model"],
        governance_triggers=governance.policy_trigger_ids,
    )


__all__ = ["Settings", "app"]

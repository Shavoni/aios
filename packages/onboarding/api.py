"""REST API Endpoints for Auto-Onboarding Wizard.

Per ONBOARD-001 spec:
- GET /onboarding/{job_id}/preview
- POST /onboarding/{job_id}/approve-and-deploy
- PATCH /onboarding/{job_id}/customize
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Any

from .wizard import (
    get_wizard,
    WizardState,
    WizardStep,
    ConfidenceLevel,
)


# ============================================================================
# Request/Response Models
# ============================================================================

class StartWizardRequest(BaseModel):
    """Request to start a new onboarding wizard."""
    organization_name: str = Field(..., description="Name of the organization")
    website_url: str = Field(..., description="Organization's website URL")
    organization_type: str = Field(
        default="municipal",
        description="Type: municipal, enterprise, nonprofit"
    )
    tenant_id: str | None = Field(
        default=None,
        description="Optional pre-assigned tenant ID"
    )


class StartWizardResponse(BaseModel):
    """Response from starting a wizard."""
    job_id: str = Field(..., description="The wizard/job ID")
    status: str
    next_step: str
    progress: float


class DepartmentCustomization(BaseModel):
    """Customization for a single department."""
    name: str
    enabled: bool | None = None
    custom_name: str | None = None
    custom_instructions: str | None = None


class CustomizeRequest(BaseModel):
    """Request to customize wizard configuration."""
    selected_template: str | None = Field(
        default=None,
        description="Template ID to use"
    )
    departments: list[DepartmentCustomization] | None = Field(
        default=None,
        description="Department customizations"
    )


class ConfidenceScoreResponse(BaseModel):
    """Confidence score in response."""
    score: float
    level: str
    reason: str
    evidence: list[str]


class AgentPreviewResponse(BaseModel):
    """Preview of an agent to be created."""
    name: str
    domain: str
    capabilities: list[str]
    model: str
    confidence: float | None = None
    is_router: bool = False


class PreviewResponse(BaseModel):
    """Full deployment preview response."""
    job_id: str
    tenant_id: str
    tenant_name: str
    status: str
    progress: float

    # Agents
    agents: list[AgentPreviewResponse]
    agent_count: int

    # Knowledge base
    kb_documents: int
    kb_sources: list[str]

    # Governance
    policies: list[str]
    hitl_rules: list[str]

    # Estimates
    estimated_monthly_cost: float
    estimated_setup_time_minutes: int

    # Review requirements
    warnings: list[str]
    requires_review: list[str]
    requires_approval: bool
    approval_checklist: list[dict[str, Any]]


class ApproveAndDeployRequest(BaseModel):
    """Request to approve and deploy."""
    skip_approval: bool = Field(
        default=False,
        description="Skip HITL approval checks (admin only)"
    )
    approved_items: list[int] | None = Field(
        default=None,
        description="List of checklist item indices to approve"
    )


class ApproveAndDeployResponse(BaseModel):
    """Response from approve and deploy."""
    job_id: str
    deployment_id: str
    status: str
    progress: float
    success: bool
    errors: list[str]
    completed_at: str | None


class WizardStatusResponse(BaseModel):
    """Current wizard status."""
    job_id: str
    step: str
    progress: float
    status: str
    organization_name: str
    created_at: str
    updated_at: str


class WizardListResponse(BaseModel):
    """List of wizards."""
    wizards: list[dict[str, Any]]
    total: int


# ============================================================================
# Router
# ============================================================================

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.post("/start", response_model=StartWizardResponse)
async def start_wizard(request: StartWizardRequest):
    """Start a new onboarding wizard.

    Creates a new wizard session for auto-onboarding an organization.
    Returns a job_id to track progress.
    """
    wizard = get_wizard()

    state = wizard.start_wizard(
        organization_name=request.organization_name,
        website_url=request.website_url,
        organization_type=request.organization_type,
        tenant_id=request.tenant_id,
    )

    return StartWizardResponse(
        job_id=state.id,
        status=state.step.value,
        next_step="discovery",
        progress=state.progress,
    )


@router.get("/jobs", response_model=WizardListResponse)
async def list_wizards(include_completed: bool = False):
    """List all onboarding wizards."""
    wizard = get_wizard()
    wizards = wizard.list_wizards(include_completed=include_completed)

    return WizardListResponse(
        wizards=wizards,
        total=len(wizards),
    )


@router.get("/{job_id}/status", response_model=WizardStatusResponse)
async def get_wizard_status(job_id: str):
    """Get current status of an onboarding wizard."""
    wizard = get_wizard()
    state = wizard.get_wizard(job_id)

    if not state:
        raise HTTPException(status_code=404, detail=f"Wizard {job_id} not found")

    return WizardStatusResponse(
        job_id=state.id,
        step=state.step.value,
        progress=state.progress,
        status=state.deployment_status or state.step.value,
        organization_name=state.organization_name,
        created_at=state.created_at,
        updated_at=state.updated_at,
    )


@router.post("/{job_id}/discover")
async def run_discovery(job_id: str, background_tasks: BackgroundTasks):
    """Run URL discovery for the organization.

    This is an async operation - check status for progress.
    """
    wizard = get_wizard()
    state = wizard.get_wizard(job_id)

    if not state:
        raise HTTPException(status_code=404, detail=f"Wizard {job_id} not found")

    # Run discovery in background
    async def _run():
        await wizard.run_discovery(job_id)

    background_tasks.add_task(lambda: __import__('asyncio').run(_run()))

    return {
        "job_id": job_id,
        "status": "discovery_started",
        "message": "Discovery started. Check status endpoint for progress.",
    }


@router.post("/{job_id}/match-templates")
async def match_templates(job_id: str):
    """Match organization to available templates."""
    wizard = get_wizard()
    state = wizard.get_wizard(job_id)

    if not state:
        raise HTTPException(status_code=404, detail=f"Wizard {job_id} not found")

    state = wizard.match_templates(job_id)

    return {
        "job_id": job_id,
        "status": state.step.value,
        "matched_templates": [t.to_dict() for t in state.matched_templates],
        "selected_template": state.selected_template,
    }


@router.patch("/{job_id}/customize")
async def customize_wizard(job_id: str, request: CustomizeRequest):
    """Customize wizard configuration.

    ONBOARD-001 spec: PATCH /onboarding/{job_id}/customize
    """
    wizard = get_wizard()
    state = wizard.get_wizard(job_id)

    if not state:
        raise HTTPException(status_code=404, detail=f"Wizard {job_id} not found")

    # Apply template selection
    if request.selected_template:
        state = wizard.select_template(job_id, request.selected_template)

    # Apply department customizations
    if request.departments:
        for dept in request.departments:
            state = wizard.update_department(
                wizard_id=job_id,
                department_name=dept.name,
                enabled=dept.enabled,
                custom_name=dept.custom_name,
                custom_instructions=dept.custom_instructions,
            )

    return {
        "job_id": job_id,
        "status": "customized",
        "selected_template": state.selected_template,
        "departments": [d.to_dict() for d in state.discovered_departments],
    }


@router.get("/{job_id}/preview", response_model=PreviewResponse)
async def get_preview(job_id: str):
    """Get deployment preview.

    ONBOARD-001 spec: GET /onboarding/{job_id}/preview

    Returns complete preview of what will be deployed including:
    - Agents to create
    - Knowledge base documents
    - Governance policies
    - Cost estimates
    - Items requiring review
    """
    wizard = get_wizard()
    state = wizard.get_wizard(job_id)

    if not state:
        raise HTTPException(status_code=404, detail=f"Wizard {job_id} not found")

    # Generate preview if not already generated
    if not state.preview or state.step.value in ("init", "discovery", "analysis", "template_match", "customization"):
        state = wizard.generate_preview(job_id)

    if not state.preview:
        raise HTTPException(status_code=400, detail="Preview could not be generated")

    # Build agent response
    agents = [
        AgentPreviewResponse(
            name=a.get("name", ""),
            domain=a.get("domain", ""),
            capabilities=a.get("capabilities", []),
            model=a.get("model", "gpt-4o-mini"),
            confidence=a.get("confidence"),
            is_router=a.get("is_router", False),
        )
        for a in state.preview.agents
    ]

    return PreviewResponse(
        job_id=state.id,
        tenant_id=state.preview.tenant_id,
        tenant_name=state.preview.tenant_name,
        status=state.step.value,
        progress=state.progress,
        agents=agents,
        agent_count=state.preview.agent_count,
        kb_documents=state.preview.kb_documents,
        kb_sources=state.preview.kb_sources,
        policies=state.preview.policies,
        hitl_rules=state.preview.hitl_rules,
        estimated_monthly_cost=state.preview.estimated_monthly_cost,
        estimated_setup_time_minutes=state.preview.estimated_setup_time_minutes,
        warnings=state.preview.warnings,
        requires_review=state.preview.requires_review,
        requires_approval=state.requires_approval,
        approval_checklist=state.approval_checklist,
    )


@router.post("/{job_id}/approve-and-deploy", response_model=ApproveAndDeployResponse)
async def approve_and_deploy(job_id: str, request: ApproveAndDeployRequest):
    """Approve checklist items and deploy.

    ONBOARD-001 spec: POST /onboarding/{job_id}/approve-and-deploy

    If there are pending checklist items:
    - Pass approved_items to approve specific items
    - Or pass skip_approval=True to skip all checks (admin only)

    Once all items are approved, deployment proceeds automatically.
    """
    wizard = get_wizard()
    state = wizard.get_wizard(job_id)

    if not state:
        raise HTTPException(status_code=404, detail=f"Wizard {job_id} not found")

    # Approve specified items
    if request.approved_items:
        for idx in request.approved_items:
            state = wizard.approve_checklist_item(job_id, idx)

    # Check if we can deploy
    if state.requires_approval and not request.skip_approval:
        pending = [c for c in state.approval_checklist if not c.get("approved")]
        if pending:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot deploy: {len(pending)} checklist item(s) pending approval"
            )

    # Execute deployment
    try:
        state = await wizard.deploy(job_id, skip_approval=request.skip_approval)

        return ApproveAndDeployResponse(
            job_id=state.id,
            deployment_id=state.deployment_id,
            status=state.deployment_status,
            progress=state.progress,
            success=state.step == WizardStep.COMPLETE,
            errors=state.deployment_errors,
            completed_at=state.completed_at or None,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deployment failed: {str(e)}")


@router.post("/{job_id}/approve-item/{item_index}")
async def approve_checklist_item(job_id: str, item_index: int):
    """Approve a single checklist item."""
    wizard = get_wizard()
    state = wizard.get_wizard(job_id)

    if not state:
        raise HTTPException(status_code=404, detail=f"Wizard {job_id} not found")

    if item_index < 0 or item_index >= len(state.approval_checklist):
        raise HTTPException(status_code=400, detail=f"Invalid item index: {item_index}")

    state = wizard.approve_checklist_item(job_id, item_index)

    return {
        "job_id": job_id,
        "item_index": item_index,
        "approved": True,
        "remaining_items": len([c for c in state.approval_checklist if not c.get("approved")]),
        "all_approved": not state.requires_approval,
    }


# ============================================================================
# Include in main app
# ============================================================================

def include_router(app):
    """Include the onboarding router in the main app."""
    app.include_router(router)


__all__ = [
    "router",
    "include_router",
    "StartWizardRequest",
    "StartWizardResponse",
    "CustomizeRequest",
    "PreviewResponse",
    "ApproveAndDeployRequest",
    "ApproveAndDeployResponse",
]

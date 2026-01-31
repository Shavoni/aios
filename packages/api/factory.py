"""
GPT Factory API Endpoints

REST API for the GPT Factory pipeline.
Integrates with existing AIOS discovery and agent systems.
"""

from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Optional, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from packages.gpt_factory import (
    GPTFactory,
    ArchetypeRegistry,
    AgentValidator,
    ExportManager,
    OrganizationType,
    ExportTarget,
)
from packages.gpt_factory.models import (
    AgentBlueprint,
    ValidationReport,
    ExportResult,
)
from packages.gpt_factory.archetypes import Archetype

# Initialize factory components
archetype_registry = ArchetypeRegistry()
archetype_registry.load_archetypes()
factory = GPTFactory(archetype_registry=archetype_registry)

router = APIRouter(prefix="/factory", tags=["GPT Factory"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class DiscoverRequest(BaseModel):
    """Request to start discovery."""
    url: str
    organization_type: OrganizationType
    mode: str = "shallow"  # shallow, full
    max_pages: int = 50
    max_depth: int = 2


class DiscoverResponse(BaseModel):
    """Response from discovery."""
    job_id: str
    status: str
    organization_name: str
    candidates_count: int
    message: str


class SelectCandidatesRequest(BaseModel):
    """Request to select candidates."""
    candidate_ids: list[str]
    approver: str = "user"


class GenerateRequest(BaseModel):
    """Request to generate blueprints."""
    overrides: Optional[dict[str, dict[str, Any]]] = None


class ApproveBlueprintsRequest(BaseModel):
    """Request to approve blueprints."""
    approver: str = "user"
    modifications: Optional[dict[str, dict[str, Any]]] = None


class PackageRequest(BaseModel):
    """Request to package agents."""
    targets: list[ExportTarget] = [ExportTarget.AIOS_NATIVE]
    output_dir: str = "data/factory/exports"


class FinalizeRequest(BaseModel):
    """Request to finalize job."""
    approver: str = "user"


class JobStatusResponse(BaseModel):
    """Job status response."""
    job_id: str
    current_stage: str
    organization_name: str
    candidates_count: int
    selected_count: int
    blueprints_count: int
    pending_checkpoint: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class ArchetypeResponse(BaseModel):
    """Archetype information."""
    id: str
    name: str
    description: str
    domain: str
    organization_types: list[str]
    candidate_types: list[str]


# =============================================================================
# DISCOVERY ENDPOINTS
# =============================================================================

@router.post("/discover", response_model=DiscoverResponse)
async def start_discovery(request: DiscoverRequest):
    """
    Start discovery for an organization.

    This crawls the organization's website to identify departments,
    leadership, and potential agent candidates.
    """
    try:
        job = await factory.discover(
            url=request.url,
            organization_type=request.organization_type,
            options={
                "mode": request.mode,
                "max_pages": request.max_pages,
                "max_depth": request.max_depth,
            }
        )

        return DiscoverResponse(
            job_id=job.job_id,
            status=job.current_stage.value,
            organization_name=job.organization.name,
            candidates_count=len(job.candidates),
            message=f"Discovered {len(job.candidates)} potential agent candidates.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get the current status of a factory job."""
    job = factory.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    pending = job.get_pending_checkpoint()
    pending_data = None
    if pending:
        pending_data = {
            "stage": pending.stage.value,
            "type": pending.checkpoint_type.value,
            "message": pending.message,
        }

    return JobStatusResponse(
        job_id=job.job_id,
        current_stage=job.current_stage.value,
        organization_name=job.organization.name,
        candidates_count=len(job.candidates),
        selected_count=len(job.selected_candidates),
        blueprints_count=len(job.blueprints),
        pending_checkpoint=pending_data,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get("/jobs/{job_id}/candidates")
async def get_candidates(job_id: str):
    """Get discovered candidates for a job."""
    job = factory.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    return {
        "job_id": job_id,
        "candidates": [c.model_dump(mode="json") for c in job.candidates],
        "selected_ids": [c.id for c in job.selected_candidates],
    }


@router.put("/jobs/{job_id}/candidates")
async def select_candidates(job_id: str, request: SelectCandidatesRequest):
    """Select which candidates to generate agents for."""
    job = factory.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    try:
        job = factory.select_candidates(
            job_id=job_id,
            selected_ids=request.candidate_ids,
            approver=request.approver,
        )

        return {
            "job_id": job_id,
            "selected_count": len(job.selected_candidates),
            "current_stage": job.current_stage.value,
            "message": f"Selected {len(job.selected_candidates)} candidates for agent generation.",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# RESEARCH ENDPOINTS
# =============================================================================

@router.post("/jobs/{job_id}/research")
async def run_research(job_id: str):
    """Run research phase to enrich selected candidates."""
    job = factory.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    try:
        job = await factory.research(job_id)

        return {
            "job_id": job_id,
            "current_stage": job.current_stage.value,
            "enriched_candidates": len(job.selected_candidates),
            "message": "Research complete. Candidates enriched with archetype matching.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# GENERATION ENDPOINTS
# =============================================================================

@router.post("/jobs/{job_id}/generate")
async def generate_blueprints(job_id: str, request: GenerateRequest = None):
    """Generate agent blueprints from selected candidates."""
    job = factory.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    request = request or GenerateRequest()

    try:
        job = factory.generate(
            job_id=job_id,
            overrides=request.overrides,
        )

        return {
            "job_id": job_id,
            "current_stage": job.current_stage.value,
            "blueprints_count": len(job.blueprints),
            "blueprints": [
                {
                    "id": b.id,
                    "name": b.name,
                    "title": b.title,
                    "domain": b.domain,
                }
                for b in job.blueprints
            ],
            "message": f"Generated {len(job.blueprints)} agent blueprints. Awaiting approval.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}/blueprints")
async def get_blueprints(job_id: str):
    """Get generated blueprints for a job."""
    job = factory.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    return {
        "job_id": job_id,
        "blueprints": [b.model_dump(mode="json") for b in job.blueprints],
    }


@router.get("/jobs/{job_id}/blueprints/{blueprint_id}")
async def get_blueprint(job_id: str, blueprint_id: str):
    """Get a specific blueprint."""
    job = factory.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    blueprint = next((b for b in job.blueprints if b.id == blueprint_id), None)
    if not blueprint:
        raise HTTPException(status_code=404, detail=f"Blueprint not found: {blueprint_id}")

    return blueprint.model_dump(mode="json")


@router.post("/jobs/{job_id}/blueprints/approve")
async def approve_blueprints(job_id: str, request: ApproveBlueprintsRequest):
    """Approve generated blueprints."""
    job = factory.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    try:
        job = factory.approve_blueprints(
            job_id=job_id,
            approver=request.approver,
            modifications=request.modifications,
        )

        return {
            "job_id": job_id,
            "current_stage": job.current_stage.value,
            "message": "Blueprints approved. Ready for validation.",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# VALIDATION ENDPOINTS
# =============================================================================

@router.post("/jobs/{job_id}/validate")
async def validate_blueprints(job_id: str):
    """Validate all blueprints in the job."""
    job = factory.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    try:
        job = factory.validate(job_id)

        # Summarize results
        results = []
        all_passed = True
        for agent_id, report in job.validation_reports.items():
            results.append({
                "agent_id": agent_id,
                "status": report.status.value,
                "overall_score": report.overall_score,
                "errors": report.error_count,
                "warnings": report.warning_count,
            })
            if report.status.value == "failed":
                all_passed = False

        return {
            "job_id": job_id,
            "current_stage": job.current_stage.value,
            "all_passed": all_passed,
            "results": results,
            "message": f"Validation {'passed' if all_passed else 'found issues'}.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}/validation")
async def get_validation_reports(job_id: str):
    """Get validation reports for a job."""
    job = factory.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    return {
        "job_id": job_id,
        "reports": {
            k: v.model_dump(mode="json")
            for k, v in job.validation_reports.items()
        },
    }


# =============================================================================
# PACKAGING ENDPOINTS
# =============================================================================

@router.post("/jobs/{job_id}/package")
async def package_agents(job_id: str, request: PackageRequest):
    """Package agents for deployment."""
    job = factory.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    try:
        output_dir = Path(request.output_dir) / job_id
        job = factory.package(
            job_id=job_id,
            targets=request.targets,
            output_dir=output_dir,
        )

        # Summarize results
        results = []
        for agent_id, targets in job.export_results.items():
            for target, result in targets.items():
                results.append({
                    "agent_id": agent_id,
                    "target": target.value,
                    "success": result.success,
                    "output_path": result.output_path,
                    "warnings": result.warnings,
                })

        return {
            "job_id": job_id,
            "current_stage": job.current_stage.value,
            "output_dir": str(output_dir),
            "results": results,
            "message": f"Packaged {len(job.blueprints)} agents. Awaiting final approval.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/finalize")
async def finalize_job(job_id: str, request: FinalizeRequest):
    """Finalize the job after packaging."""
    job = factory.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    try:
        job = factory.finalize(job_id, approver=request.approver)

        return {
            "job_id": job_id,
            "status": "finalized",
            "blueprints_count": len(job.blueprints),
            "message": "Job finalized. Agents ready for deployment.",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# DEPLOYMENT ENDPOINTS
# =============================================================================

@router.post("/jobs/{job_id}/deploy")
async def deploy_to_aios(job_id: str, background_tasks: BackgroundTasks):
    """Deploy generated agents to AIOS."""
    job = factory.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    # Check job is finalized
    pending = job.get_pending_checkpoint()
    if pending:
        raise HTTPException(
            status_code=400,
            detail=f"Job has pending checkpoint at stage: {pending.stage.value}"
        )

    # TODO: Integrate with AgentManager to create actual agents
    # This would:
    # 1. Convert blueprints to AgentConfig
    # 2. Register with AgentManager
    # 3. Initialize knowledge bases
    # 4. Update Concierge routing

    return {
        "job_id": job_id,
        "status": "deployment_started",
        "agents": [b.id for b in job.blueprints],
        "message": "Deployment initiated. Agents will be available shortly.",
    }


# =============================================================================
# ARCHETYPE ENDPOINTS
# =============================================================================

@router.get("/archetypes", response_model=list[ArchetypeResponse])
async def list_archetypes():
    """List all available archetypes."""
    archetypes = archetype_registry.list_all()
    return [
        ArchetypeResponse(
            id=a.id,
            name=a.name,
            description=a.description,
            domain=a.domain,
            organization_types=[t.value for t in a.organization_types],
            candidate_types=[t.value for t in a.candidate_types],
        )
        for a in archetypes
    ]


@router.get("/archetypes/{archetype_id}")
async def get_archetype(archetype_id: str):
    """Get a specific archetype."""
    archetype = archetype_registry.get(archetype_id)
    if not archetype:
        raise HTTPException(status_code=404, detail=f"Archetype not found: {archetype_id}")

    return archetype.model_dump(mode="json")


@router.get("/archetypes/for/{organization_type}")
async def get_archetypes_for_org(organization_type: OrganizationType):
    """Get archetypes applicable to an organization type."""
    archetypes = archetype_registry.for_organization_type(organization_type)
    return [
        ArchetypeResponse(
            id=a.id,
            name=a.name,
            description=a.description,
            domain=a.domain,
            organization_types=[t.value for t in a.organization_types],
            candidate_types=[t.value for t in a.candidate_types],
        )
        for a in archetypes
    ]


# =============================================================================
# UTILITY ENDPOINTS
# =============================================================================

@router.get("/jobs")
async def list_jobs():
    """List all factory jobs."""
    jobs = factory.list_jobs()
    return {
        "jobs": [j.to_dict() for j in jobs],
    }


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a factory job."""
    if job_id not in factory.jobs:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    del factory.jobs[job_id]
    return {"message": f"Job {job_id} deleted."}

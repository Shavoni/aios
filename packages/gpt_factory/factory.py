"""
GPT Factory

Main orchestrator for the agent generation pipeline.
Coordinates discovery, research, generation, validation, and export.
"""

from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Callable
from enum import Enum
import json

from .models import (
    Organization,
    OrganizationType,
    AgentCandidate,
    CandidateType,
    AgentBlueprint,
    ValidationReport,
    ExportTarget,
    ExportResult,
)
from .archetypes import ArchetypeRegistry, Archetype
from .templates import TemplateEngine
from .validation import AgentValidator
from .exporters import ExportManager


class PipelineStage(str, Enum):
    """Stages in the GPT Factory pipeline."""
    DISCOVER = "discover"
    RESEARCH = "research"
    GENERATE = "generate"
    VALIDATE = "validate"
    PACKAGE = "package"


class CheckpointType(str, Enum):
    """Types of checkpoints in the pipeline."""
    HUMAN = "human"      # Requires human approval
    SYSTEM = "system"    # Automatic system checkpoint
    NONE = "none"        # No checkpoint


class PipelineCheckpoint:
    """A checkpoint in the pipeline for human review or system validation."""

    def __init__(
        self,
        stage: PipelineStage,
        checkpoint_type: CheckpointType,
        data: dict[str, Any],
        message: str = "",
    ):
        self.stage = stage
        self.checkpoint_type = checkpoint_type
        self.data = data
        self.message = message
        self.timestamp = datetime.utcnow()
        self.approved = False
        self.approved_by: Optional[str] = None
        self.approved_at: Optional[datetime] = None

    def approve(self, approver: str = "system") -> None:
        """Approve this checkpoint."""
        self.approved = True
        self.approved_by = approver
        self.approved_at = datetime.utcnow()


class FactoryJob:
    """
    Tracks the state of an agent generation job.

    A job progresses through pipeline stages, with checkpoints for review.
    """

    def __init__(self, job_id: str, organization: Organization):
        self.job_id = job_id
        self.organization = organization
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

        # Pipeline state
        self.current_stage = PipelineStage.DISCOVER
        self.checkpoints: list[PipelineCheckpoint] = []

        # Outputs from each stage
        self.candidates: list[AgentCandidate] = []
        self.selected_candidates: list[AgentCandidate] = []
        self.blueprints: list[AgentBlueprint] = []
        self.validation_reports: dict[str, ValidationReport] = {}
        self.export_results: dict[str, dict[ExportTarget, ExportResult]] = {}

        # Metadata
        self.metadata: dict[str, Any] = {}

    def add_checkpoint(self, checkpoint: PipelineCheckpoint) -> None:
        """Add a checkpoint to the job."""
        self.checkpoints.append(checkpoint)
        self.updated_at = datetime.utcnow()

    def get_pending_checkpoint(self) -> Optional[PipelineCheckpoint]:
        """Get the current pending checkpoint, if any."""
        for checkpoint in reversed(self.checkpoints):
            if not checkpoint.approved:
                return checkpoint
        return None

    def to_dict(self) -> dict[str, Any]:
        """Serialize job state to dictionary."""
        return {
            "job_id": self.job_id,
            "organization": self.organization.model_dump(mode="json"),
            "current_stage": self.current_stage.value,
            "candidates_count": len(self.candidates),
            "selected_count": len(self.selected_candidates),
            "blueprints_count": len(self.blueprints),
            "checkpoints": [
                {
                    "stage": c.stage.value,
                    "type": c.checkpoint_type.value,
                    "approved": c.approved,
                    "message": c.message,
                }
                for c in self.checkpoints
            ],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class GPTFactory:
    """
    Main factory for generating AI agents from organizational discovery.

    Pipeline:
        DISCOVER → RESEARCH → GENERATE → VALIDATE → PACKAGE

    Each stage has configurable checkpoints for human review.
    """

    def __init__(
        self,
        archetype_registry: Optional[ArchetypeRegistry] = None,
        discovery_callback: Optional[Callable] = None,
    ):
        self.archetype_registry = archetype_registry or ArchetypeRegistry()
        self.template_engine = TemplateEngine(self.archetype_registry)
        self.validator = AgentValidator()
        self.export_manager = ExportManager()

        # Discovery integration (connects to existing AIOS discovery)
        self.discovery_callback = discovery_callback

        # Active jobs
        self.jobs: dict[str, FactoryJob] = {}

        # Checkpoint configuration
        self.checkpoint_config = {
            PipelineStage.DISCOVER: CheckpointType.HUMAN,   # Review discovered candidates
            PipelineStage.RESEARCH: CheckpointType.SYSTEM,  # Auto-validate research
            PipelineStage.GENERATE: CheckpointType.HUMAN,   # Review generated configs
            PipelineStage.VALIDATE: CheckpointType.SYSTEM,  # Auto-validate
            PipelineStage.PACKAGE: CheckpointType.HUMAN,    # Final review before deploy
        }

    # =========================================================================
    # STAGE 1: DISCOVERY
    # =========================================================================

    async def discover(
        self,
        url: str,
        organization_type: OrganizationType,
        options: Optional[dict[str, Any]] = None,
    ) -> FactoryJob:
        """
        Start discovery for an organization.

        This stage crawls the organization's website to identify:
        - Organizational structure
        - Departments and divisions
        - Leadership and key contacts
        - Potential agent candidates

        Args:
            url: The organization's website URL
            organization_type: Type of organization
            options: Discovery options (depth, max_pages, etc.)

        Returns:
            FactoryJob with discovered candidates
        """
        options = options or {}

        # Create organization record
        org = Organization(
            id=self._generate_id(url),
            name=self._extract_org_name(url),
            type=organization_type,
            url=url,
        )

        # Create job
        job_id = f"job-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        job = FactoryJob(job_id, org)
        self.jobs[job_id] = job

        # Run discovery (integrate with existing AIOS discovery)
        if self.discovery_callback:
            discovery_result = await self.discovery_callback(url, options)
            job.candidates = self._convert_discovery_results(discovery_result, org)
        else:
            # Fallback: Create sample candidates based on org type
            job.candidates = self._generate_default_candidates(org)

        # Update organization with discovery metadata
        job.organization.pages_crawled = options.get("max_pages", 50)
        job.organization.discovery_depth = options.get("max_depth", 2)
        job.organization.discovered_at = datetime.utcnow()

        # Create checkpoint
        checkpoint = PipelineCheckpoint(
            stage=PipelineStage.DISCOVER,
            checkpoint_type=self.checkpoint_config[PipelineStage.DISCOVER],
            data={"candidates": [c.model_dump(mode="json") for c in job.candidates]},
            message=f"Discovered {len(job.candidates)} potential agent candidates. Please review and select.",
        )
        job.add_checkpoint(checkpoint)

        return job

    def select_candidates(
        self,
        job_id: str,
        selected_ids: list[str],
        approver: str = "user",
    ) -> FactoryJob:
        """
        Select which candidates to generate agents for.

        Args:
            job_id: The job ID
            selected_ids: IDs of candidates to generate
            approver: Who is approving this selection

        Returns:
            Updated FactoryJob
        """
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        # Update selection
        job.selected_candidates = [
            c for c in job.candidates if c.id in selected_ids
        ]

        # Mark candidates as selected
        for candidate in job.candidates:
            candidate.selected = candidate.id in selected_ids

        # Approve checkpoint
        checkpoint = job.get_pending_checkpoint()
        if checkpoint and checkpoint.stage == PipelineStage.DISCOVER:
            checkpoint.approve(approver)

        job.current_stage = PipelineStage.RESEARCH
        job.updated_at = datetime.utcnow()

        return job

    # =========================================================================
    # STAGE 2: RESEARCH
    # =========================================================================

    async def research(self, job_id: str) -> FactoryJob:
        """
        Research additional context for selected candidates.

        This stage gathers:
        - Department-specific policies and procedures
        - Contact information
        - Service descriptions
        - Related documents

        Args:
            job_id: The job ID

        Returns:
            Updated FactoryJob with enriched candidates
        """
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        # Research each selected candidate
        for candidate in job.selected_candidates:
            # Match to archetype
            archetype = self.archetype_registry.best_match(
                job.organization.type,
                candidate.type,
            )
            if archetype:
                candidate.archetype_id = archetype.id

            # TODO: Implement actual research
            # - Crawl department pages
            # - Extract policies and documents
            # - Enrich contact information
            # For now, just match archetypes

        # Create system checkpoint
        checkpoint = PipelineCheckpoint(
            stage=PipelineStage.RESEARCH,
            checkpoint_type=CheckpointType.SYSTEM,
            data={"enriched_candidates": len(job.selected_candidates)},
            message="Research complete. Candidates enriched with archetype matching.",
        )
        checkpoint.approve("system")
        job.add_checkpoint(checkpoint)

        job.current_stage = PipelineStage.GENERATE
        job.updated_at = datetime.utcnow()

        return job

    # =========================================================================
    # STAGE 3: GENERATE
    # =========================================================================

    def generate(
        self,
        job_id: str,
        overrides: Optional[dict[str, dict[str, Any]]] = None,
    ) -> FactoryJob:
        """
        Generate agent blueprints from selected candidates.

        This stage:
        - Applies archetypes to candidates
        - Generates instructions, capabilities, guardrails
        - Creates complete agent configurations

        Args:
            job_id: The job ID
            overrides: Optional per-candidate field overrides

        Returns:
            Updated FactoryJob with generated blueprints
        """
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        overrides = overrides or {}
        job.blueprints = []

        for candidate in job.selected_candidates:
            # Get archetype
            archetype = None
            if candidate.archetype_id:
                archetype = self.archetype_registry.get(candidate.archetype_id)

            # Generate blueprint
            candidate_overrides = overrides.get(candidate.id, {})
            blueprint = self.template_engine.generate_blueprint(
                candidate=candidate,
                organization=job.organization,
                archetype=archetype,
                overrides=candidate_overrides,
            )

            job.blueprints.append(blueprint)

        # Create checkpoint
        checkpoint = PipelineCheckpoint(
            stage=PipelineStage.GENERATE,
            checkpoint_type=self.checkpoint_config[PipelineStage.GENERATE],
            data={"blueprints": [b.model_dump(mode="json") for b in job.blueprints]},
            message=f"Generated {len(job.blueprints)} agent configurations. Please review.",
        )
        job.add_checkpoint(checkpoint)

        return job

    def approve_blueprints(
        self,
        job_id: str,
        approver: str = "user",
        modifications: Optional[dict[str, dict[str, Any]]] = None,
    ) -> FactoryJob:
        """
        Approve generated blueprints, optionally with modifications.

        Args:
            job_id: The job ID
            approver: Who is approving
            modifications: Optional modifications to blueprints

        Returns:
            Updated FactoryJob
        """
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        # Apply modifications
        if modifications:
            for blueprint in job.blueprints:
                if blueprint.id in modifications:
                    for key, value in modifications[blueprint.id].items():
                        if hasattr(blueprint, key):
                            setattr(blueprint, key, value)
                            blueprint.updated_at = datetime.utcnow()

        # Approve checkpoint
        checkpoint = job.get_pending_checkpoint()
        if checkpoint and checkpoint.stage == PipelineStage.GENERATE:
            checkpoint.approve(approver)

        job.current_stage = PipelineStage.VALIDATE
        job.updated_at = datetime.utcnow()

        return job

    # =========================================================================
    # STAGE 4: VALIDATE
    # =========================================================================

    def validate(self, job_id: str) -> FactoryJob:
        """
        Validate all generated blueprints.

        This stage:
        - Runs validation rules
        - Checks instructions, guardrails, governance
        - Generates validation reports

        Args:
            job_id: The job ID

        Returns:
            Updated FactoryJob with validation reports
        """
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        job.validation_reports = {}
        all_passed = True

        for blueprint in job.blueprints:
            report = self.validator.validate(blueprint)
            job.validation_reports[blueprint.id] = report

            if report.status.value == "failed":
                all_passed = False

        # Create checkpoint
        checkpoint = PipelineCheckpoint(
            stage=PipelineStage.VALIDATE,
            checkpoint_type=CheckpointType.SYSTEM,
            data={
                "reports": {
                    k: v.model_dump(mode="json")
                    for k, v in job.validation_reports.items()
                }
            },
            message=f"Validation {'passed' if all_passed else 'found issues'}.",
        )
        if all_passed:
            checkpoint.approve("system")
        job.add_checkpoint(checkpoint)

        job.current_stage = PipelineStage.PACKAGE
        job.updated_at = datetime.utcnow()

        return job

    # =========================================================================
    # STAGE 5: PACKAGE
    # =========================================================================

    def package(
        self,
        job_id: str,
        targets: list[ExportTarget],
        output_dir: Path,
    ) -> FactoryJob:
        """
        Package agents for deployment to target platforms.

        This stage:
        - Exports blueprints to specified formats
        - Applies platform-specific constraints
        - Generates deployment artifacts

        Args:
            job_id: The job ID
            targets: Export targets (AIOS_NATIVE, OPENAI_GPT, etc.)
            output_dir: Directory for output files

        Returns:
            Updated FactoryJob with export results
        """
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        job.export_results = {}

        for blueprint in job.blueprints:
            job.export_results[blueprint.id] = {}

            for target in targets:
                blueprint_dir = output_dir / blueprint.id
                result = self.export_manager.export(blueprint, target, blueprint_dir)
                job.export_results[blueprint.id][target] = result

        # Create final checkpoint
        checkpoint = PipelineCheckpoint(
            stage=PipelineStage.PACKAGE,
            checkpoint_type=self.checkpoint_config[PipelineStage.PACKAGE],
            data={"export_results": self._serialize_export_results(job.export_results)},
            message=f"Packaged {len(job.blueprints)} agents for {len(targets)} platform(s). Ready for deployment.",
        )
        job.add_checkpoint(checkpoint)

        return job

    def finalize(self, job_id: str, approver: str = "user") -> FactoryJob:
        """
        Finalize the job after packaging.

        Args:
            job_id: The job ID
            approver: Who is approving

        Returns:
            Finalized FactoryJob
        """
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        # Approve final checkpoint
        checkpoint = job.get_pending_checkpoint()
        if checkpoint and checkpoint.stage == PipelineStage.PACKAGE:
            checkpoint.approve(approver)

        job.updated_at = datetime.utcnow()

        return job

    # =========================================================================
    # UTILITIES
    # =========================================================================

    def _generate_id(self, url: str) -> str:
        """Generate an ID from URL."""
        import hashlib
        return hashlib.sha256(url.encode()).hexdigest()[:12]

    def _extract_org_name(self, url: str) -> str:
        """Extract organization name from URL."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        # Convert domain to title case name
        name = domain.split(".")[0].replace("-", " ").title()
        return name

    def _convert_discovery_results(
        self,
        discovery_result: Any,
        org: Organization,
    ) -> list[AgentCandidate]:
        """Convert AIOS discovery results to factory candidates."""
        # This would integrate with existing discovery system
        # For now, return empty list (implement based on your discovery output)
        return []

    def _generate_default_candidates(
        self,
        org: Organization,
    ) -> list[AgentCandidate]:
        """Generate default candidates based on organization type."""
        candidates = []

        # Get applicable archetypes
        archetypes = self.archetype_registry.for_organization_type(org.type)

        for archetype in archetypes:
            for candidate_type in archetype.candidate_types:
                candidate = AgentCandidate(
                    id=f"{org.id}-{candidate_type.value}",
                    organization_id=org.id,
                    name=archetype.name,
                    suggested_agent_name=archetype.name,
                    type=candidate_type,
                    confidence=0.8,  # Default confidence for archetype matches
                    source_urls=[org.url],
                    archetype_id=archetype.id,
                )
                candidates.append(candidate)

        return candidates

    def _serialize_export_results(
        self,
        results: dict[str, dict[ExportTarget, ExportResult]],
    ) -> dict[str, Any]:
        """Serialize export results for checkpoint data."""
        serialized = {}
        for agent_id, targets in results.items():
            serialized[agent_id] = {
                t.value: r.model_dump(mode="json")
                for t, r in targets.items()
            }
        return serialized

    def get_job(self, job_id: str) -> Optional[FactoryJob]:
        """Get a job by ID."""
        return self.jobs.get(job_id)

    def list_jobs(self) -> list[FactoryJob]:
        """List all jobs."""
        return list(self.jobs.values())

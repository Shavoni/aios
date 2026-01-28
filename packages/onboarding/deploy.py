"""Deployment Orchestrator for aiOS municipal deployments."""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from packages.onboarding.manifest import DeploymentManifest


class DeploymentStep(str, Enum):
    """Deployment steps."""
    VALIDATE = "validate"
    PROVISION_TENANT = "provision_tenant"
    DEPLOY_GOVERNANCE = "deploy_governance"
    CREATE_AGENTS = "create_agents"
    CONNECT_DATA_SOURCES = "connect_data_sources"
    INITIAL_SYNC = "initial_sync"
    CONFIGURE_CONCIERGE = "configure_concierge"
    SMOKE_TESTS = "smoke_tests"
    FINALIZE = "finalize"


class DeploymentStatus(str, Enum):
    """Status of a deployment."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class DeploymentProgress:
    """Progress update for deployment."""
    step: DeploymentStep
    step_number: int
    total_steps: int
    status: str
    message: str
    progress_percent: int
    timestamp: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class DeploymentResult:
    """Result of a deployment."""
    id: str
    manifest_id: str
    status: DeploymentStatus
    started_at: str
    completed_at: str | None = None
    current_step: DeploymentStep | None = None
    progress: list[DeploymentProgress] = field(default_factory=list)
    error: str | None = None
    rollback_performed: bool = False
    created_agents: list[str] = field(default_factory=list)
    connected_sources: list[str] = field(default_factory=list)
    report: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "manifest_id": self.manifest_id,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "current_step": self.current_step.value if self.current_step else None,
            "progress": [
                {
                    "step": p.step.value,
                    "step_number": p.step_number,
                    "total_steps": p.total_steps,
                    "status": p.status,
                    "message": p.message,
                    "progress_percent": p.progress_percent,
                    "timestamp": p.timestamp,
                    "details": p.details,
                }
                for p in self.progress
            ],
            "error": self.error,
            "rollback_performed": self.rollback_performed,
            "created_agents": self.created_agents,
            "connected_sources": self.connected_sources,
            "report": self.report,
        }


class DeploymentOrchestrator:
    """Orchestrates the deployment of aiOS configurations."""

    DEPLOYMENT_STEPS = [
        DeploymentStep.VALIDATE,
        DeploymentStep.PROVISION_TENANT,
        DeploymentStep.DEPLOY_GOVERNANCE,
        DeploymentStep.CREATE_AGENTS,
        DeploymentStep.CONNECT_DATA_SOURCES,
        DeploymentStep.INITIAL_SYNC,
        DeploymentStep.CONFIGURE_CONCIERGE,
        DeploymentStep.SMOKE_TESTS,
        DeploymentStep.FINALIZE,
    ]

    def __init__(self, storage_path: Path | None = None) -> None:
        self.storage_path = storage_path or Path("data/onboarding/deployments")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._deployments: dict[str, DeploymentResult] = {}
        self._progress_callbacks: dict[str, list[Callable[[DeploymentProgress], None]]] = {}
        self._load_deployments()

    def _load_deployments(self) -> None:
        """Load existing deployments from storage."""
        for filepath in self.storage_path.glob("deploy-*.json"):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    deploy_id = data.get("id")
                    if deploy_id:
                        self._deployments[deploy_id] = self._dict_to_result(data)
            except Exception:
                continue

    def _dict_to_result(self, data: dict) -> DeploymentResult:
        """Convert dictionary to DeploymentResult."""
        result = DeploymentResult(
            id=data.get("id", ""),
            manifest_id=data.get("manifest_id", ""),
            status=DeploymentStatus(data.get("status", "pending")),
            started_at=data.get("started_at", ""),
            completed_at=data.get("completed_at"),
            current_step=DeploymentStep(data["current_step"]) if data.get("current_step") else None,
            error=data.get("error"),
            rollback_performed=data.get("rollback_performed", False),
            created_agents=data.get("created_agents", []),
            connected_sources=data.get("connected_sources", []),
            report=data.get("report", {}),
        )

        for p in data.get("progress", []):
            result.progress.append(DeploymentProgress(
                step=DeploymentStep(p.get("step")),
                step_number=p.get("step_number", 0),
                total_steps=p.get("total_steps", 9),
                status=p.get("status", ""),
                message=p.get("message", ""),
                progress_percent=p.get("progress_percent", 0),
                timestamp=p.get("timestamp", ""),
                details=p.get("details", {}),
            ))

        return result

    def _save_deployment(self, result: DeploymentResult) -> None:
        """Save deployment to storage."""
        filepath = self.storage_path / f"{result.id}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, indent=2)

    def _generate_deploy_id(self, manifest_id: str) -> str:
        """Generate a deployment ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"deploy-{manifest_id.replace('manifest-', '')}-{timestamp}"

    def start_deployment(
        self,
        manifest: DeploymentManifest,
        progress_callback: Callable[[DeploymentProgress], None] | None = None,
    ) -> str:
        """Start a deployment.

        Args:
            manifest: The deployment manifest to deploy
            progress_callback: Optional callback for progress updates

        Returns:
            Deployment ID for tracking
        """
        deploy_id = self._generate_deploy_id(manifest.id)

        result = DeploymentResult(
            id=deploy_id,
            manifest_id=manifest.id,
            status=DeploymentStatus.PENDING,
            started_at=datetime.utcnow().isoformat(),
        )
        self._deployments[deploy_id] = result

        if progress_callback:
            self._progress_callbacks[deploy_id] = [progress_callback]

        self._save_deployment(result)

        # Start deployment in background thread
        thread = threading.Thread(
            target=self._run_deployment,
            args=(deploy_id, manifest),
            daemon=True,
        )
        thread.start()

        return deploy_id

    def get_status(self, deploy_id: str) -> DeploymentResult | None:
        """Get the status of a deployment."""
        return self._deployments.get(deploy_id)

    def add_progress_callback(
        self, deploy_id: str, callback: Callable[[DeploymentProgress], None]
    ) -> None:
        """Add a progress callback for a deployment."""
        if deploy_id not in self._progress_callbacks:
            self._progress_callbacks[deploy_id] = []
        self._progress_callbacks[deploy_id].append(callback)

    def _emit_progress(self, deploy_id: str, progress: DeploymentProgress) -> None:
        """Emit a progress update."""
        result = self._deployments.get(deploy_id)
        if result:
            result.progress.append(progress)
            result.current_step = progress.step
            self._save_deployment(result)

        for callback in self._progress_callbacks.get(deploy_id, []):
            try:
                callback(progress)
            except Exception:
                pass

    def _run_deployment(self, deploy_id: str, manifest: DeploymentManifest) -> None:
        """Run the deployment process."""
        result = self._deployments[deploy_id]
        result.status = DeploymentStatus.IN_PROGRESS
        total_steps = len(self.DEPLOYMENT_STEPS)

        try:
            for i, step in enumerate(self.DEPLOYMENT_STEPS):
                step_num = i + 1
                progress_percent = int((step_num / total_steps) * 100)

                # Emit starting progress
                self._emit_progress(deploy_id, DeploymentProgress(
                    step=step,
                    step_number=step_num,
                    total_steps=total_steps,
                    status="in_progress",
                    message=f"Starting: {step.value.replace('_', ' ').title()}",
                    progress_percent=progress_percent - 5,
                    timestamp=datetime.utcnow().isoformat(),
                ))

                # Execute step
                step_result = self._execute_step(deploy_id, step, manifest, result)

                # Emit completion progress
                self._emit_progress(deploy_id, DeploymentProgress(
                    step=step,
                    step_number=step_num,
                    total_steps=total_steps,
                    status="completed",
                    message=f"Completed: {step.value.replace('_', ' ').title()}",
                    progress_percent=progress_percent,
                    timestamp=datetime.utcnow().isoformat(),
                    details=step_result,
                ))

            # Deployment completed
            result.status = DeploymentStatus.COMPLETED
            result.completed_at = datetime.utcnow().isoformat()
            result.report = self._generate_report(manifest, result)

        except Exception as e:
            result.status = DeploymentStatus.FAILED
            result.error = str(e)
            result.completed_at = datetime.utcnow().isoformat()

            # Attempt rollback
            self._rollback(deploy_id, result)

        self._save_deployment(result)

    def _execute_step(
        self,
        deploy_id: str,
        step: DeploymentStep,
        manifest: DeploymentManifest,
        result: DeploymentResult,
    ) -> dict[str, Any]:
        """Execute a single deployment step."""
        step_handlers = {
            DeploymentStep.VALIDATE: self._step_validate,
            DeploymentStep.PROVISION_TENANT: self._step_provision_tenant,
            DeploymentStep.DEPLOY_GOVERNANCE: self._step_deploy_governance,
            DeploymentStep.CREATE_AGENTS: self._step_create_agents,
            DeploymentStep.CONNECT_DATA_SOURCES: self._step_connect_data_sources,
            DeploymentStep.INITIAL_SYNC: self._step_initial_sync,
            DeploymentStep.CONFIGURE_CONCIERGE: self._step_configure_concierge,
            DeploymentStep.SMOKE_TESTS: self._step_smoke_tests,
            DeploymentStep.FINALIZE: self._step_finalize,
        }

        handler = step_handlers.get(step)
        if handler:
            return handler(manifest, result)
        return {}

    def _step_validate(
        self, manifest: DeploymentManifest, result: DeploymentResult
    ) -> dict[str, Any]:
        """Validate the manifest before deployment."""
        errors = []

        if not manifest.agents:
            errors.append("No agents defined in manifest")

        if not manifest.concierge:
            errors.append("No concierge configuration")

        if errors:
            raise ValueError(f"Manifest validation failed: {', '.join(errors)}")

        return {
            "agents_count": len(manifest.agents),
            "data_sources_count": len(manifest.data_sources),
            "validation": "passed",
        }

    def _step_provision_tenant(
        self, manifest: DeploymentManifest, result: DeploymentResult
    ) -> dict[str, Any]:
        """Provision tenant resources."""
        # In a real implementation, this would:
        # - Create database schemas
        # - Set up authentication
        # - Configure storage

        # Simulate work
        time.sleep(0.5)

        return {
            "tenant_id": f"tenant-{manifest.municipality_name.lower().replace(' ', '-')}",
            "provisioned": True,
        }

    def _step_deploy_governance(
        self, manifest: DeploymentManifest, result: DeploymentResult
    ) -> dict[str, Any]:
        """Deploy governance framework."""
        # In a real implementation, this would:
        # - Load governance policies
        # - Configure sensitivity rules
        # - Set up guardrails

        time.sleep(0.3)

        return {
            "policies_loaded": True,
            "sensitivity_rules": list(manifest.governance.sensitivity_rules.keys()) if manifest.governance else [],
        }

    def _step_create_agents(
        self, manifest: DeploymentManifest, result: DeploymentResult
    ) -> dict[str, Any]:
        """Create agents from manifest."""
        from packages.core.agents import AgentConfig, get_agent_manager

        manager = get_agent_manager()
        created = []

        for agent_manifest in manifest.agents:
            # Check if agent already exists
            existing = manager.get_agent(agent_manifest.id)
            if existing:
                # Update existing agent
                manager.update_agent(agent_manifest.id, {
                    "name": agent_manifest.name,
                    "title": agent_manifest.title,
                    "domain": agent_manifest.domain,
                    "description": agent_manifest.description,
                    "system_prompt": agent_manifest.system_prompt,
                    "capabilities": agent_manifest.capabilities,
                    "guardrails": agent_manifest.guardrails,
                    "escalates_to": agent_manifest.escalates_to,
                    "status": "active",
                })
            else:
                # Create new agent
                config = AgentConfig(
                    id=agent_manifest.id,
                    name=agent_manifest.name,
                    title=agent_manifest.title,
                    domain=agent_manifest.domain,
                    description=agent_manifest.description,
                    system_prompt=agent_manifest.system_prompt,
                    capabilities=agent_manifest.capabilities,
                    guardrails=agent_manifest.guardrails,
                    escalates_to=agent_manifest.escalates_to,
                    status="active",
                )
                manager.create_agent(config)

            created.append(agent_manifest.id)
            result.created_agents.append(agent_manifest.id)

            # Small delay between agents
            time.sleep(0.1)

        return {
            "agents_created": len(created),
            "agent_ids": created,
        }

    def _step_connect_data_sources(
        self, manifest: DeploymentManifest, result: DeploymentResult
    ) -> dict[str, Any]:
        """Connect data sources to agents."""
        # In a real implementation, this would:
        # - Configure data source connections
        # - Set up sync schedules
        # - Verify API access

        connected = []
        for source in manifest.data_sources:
            connected.append(source["id"])
            result.connected_sources.append(source["id"])
            time.sleep(0.1)

        return {
            "sources_connected": len(connected),
            "source_ids": connected,
        }

    def _step_initial_sync(
        self, manifest: DeploymentManifest, result: DeploymentResult
    ) -> dict[str, Any]:
        """Run initial data sync."""
        # In a real implementation, this would:
        # - Fetch initial data from sources
        # - Index content into knowledge bases
        # - Verify data integrity

        time.sleep(0.5)

        return {
            "sync_completed": True,
            "sources_synced": len(manifest.data_sources),
        }

    def _step_configure_concierge(
        self, manifest: DeploymentManifest, result: DeploymentResult
    ) -> dict[str, Any]:
        """Configure the Concierge router."""
        from packages.core.agents import AgentConfig, get_agent_manager

        if not manifest.concierge:
            return {"concierge": "skipped"}

        manager = get_agent_manager()

        # Build Concierge agent config
        config = AgentConfig(
            id="concierge",
            name=manifest.concierge.name,
            title=manifest.concierge.title,
            domain=manifest.concierge.domain,
            description=f"Routes staff to the correct department leadership asset for {manifest.municipality_name}",
            system_prompt=manifest.concierge.system_prompt,
            capabilities=[
                "Intent classification",
                "Department routing",
                "Risk triage",
                "Safe next-step guidance",
            ],
            guardrails=[
                "Minimal clarifying questions",
                "No speculation on policy",
                "Escalate high-risk to human",
            ],
            escalates_to="Department Leadership",
            is_router=True,
            status="active",
        )

        # Update or create
        existing = manager.get_agent("concierge")
        if existing:
            manager.update_agent("concierge", config.model_dump(exclude={"id", "created_at"}))
        else:
            manager.create_agent(config)

        return {
            "concierge_configured": True,
            "routing_rules": len(manifest.concierge.routing_rules),
        }

    def _step_smoke_tests(
        self, manifest: DeploymentManifest, result: DeploymentResult
    ) -> dict[str, Any]:
        """Run smoke tests to verify deployment."""
        from packages.core.agents import get_agent_manager

        manager = get_agent_manager()
        tests_passed = 0
        tests_failed = 0
        test_results = []

        # Test 1: Verify all agents exist
        for agent_id in result.created_agents:
            agent = manager.get_agent(agent_id)
            if agent:
                tests_passed += 1
                test_results.append({"test": f"agent_{agent_id}_exists", "passed": True})
            else:
                tests_failed += 1
                test_results.append({"test": f"agent_{agent_id}_exists", "passed": False})

        # Test 2: Verify Concierge exists
        concierge = manager.get_agent("concierge")
        if concierge:
            tests_passed += 1
            test_results.append({"test": "concierge_exists", "passed": True})
        else:
            tests_failed += 1
            test_results.append({"test": "concierge_exists", "passed": False})

        if tests_failed > 0:
            raise ValueError(f"Smoke tests failed: {tests_failed} failures")

        return {
            "tests_passed": tests_passed,
            "tests_failed": tests_failed,
            "results": test_results,
        }

    def _step_finalize(
        self, manifest: DeploymentManifest, result: DeploymentResult
    ) -> dict[str, Any]:
        """Finalize the deployment."""
        time.sleep(0.2)

        return {
            "finalized": True,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _rollback(self, deploy_id: str, result: DeploymentResult) -> None:
        """Attempt to rollback a failed deployment."""
        from packages.core.agents import get_agent_manager

        try:
            manager = get_agent_manager()

            # Remove created agents (except concierge)
            for agent_id in result.created_agents:
                if agent_id != "concierge":
                    try:
                        manager.delete_agent(agent_id)
                    except Exception:
                        pass

            result.rollback_performed = True
        except Exception:
            pass

    def _generate_report(
        self, manifest: DeploymentManifest, result: DeploymentResult
    ) -> dict[str, Any]:
        """Generate a deployment completion report."""
        return {
            "deployment_id": result.id,
            "municipality": manifest.municipality_name,
            "completed_at": result.completed_at,
            "summary": {
                "agents_deployed": len(result.created_agents),
                "data_sources_connected": len(result.connected_sources),
                "concierge_configured": True,
                "governance_deployed": True,
            },
            "agents": [
                {"id": agent.id, "name": agent.name, "domain": agent.domain}
                for agent in manifest.agents
            ],
            "next_steps": [
                "Review agent configurations in the dashboard",
                "Test routing through the chat interface",
                "Upload additional knowledge base documents",
                "Configure user access and permissions",
            ],
        }


# Module-level singleton
_orchestrator: DeploymentOrchestrator | None = None


def get_orchestrator() -> DeploymentOrchestrator:
    """Get the deployment orchestrator singleton."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = DeploymentOrchestrator()
    return _orchestrator


def start_deployment(
    manifest: DeploymentManifest,
    progress_callback: Callable[[DeploymentProgress], None] | None = None,
) -> str:
    """Start a deployment."""
    return get_orchestrator().start_deployment(manifest, progress_callback)


def get_deployment_status(deploy_id: str) -> DeploymentResult | None:
    """Get deployment status."""
    return get_orchestrator().get_status(deploy_id)

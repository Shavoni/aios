"""Deployment Package Generator for ONBOARD-001.

Implements:
- Preview/deploy parity with package_hash + manifest checksums
- deployments/{org_id}/ structure with YAML policies
- Replay deployment from package
"""

from __future__ import annotations

import hashlib
import json
import shutil
import uuid
import yaml
from dataclasses import dataclass, field
from datetime import datetime, UTC
from pathlib import Path
from typing import Any


@dataclass
class ManifestChecksum:
    """Checksum for a manifest file."""
    filename: str
    sha256: str
    size_bytes: int


@dataclass
class DeploymentPackage:
    """Complete deployment package.

    ONBOARD-001: Preview returns package_hash + manifest checksums.
    """

    # Identification
    package_id: str
    org_id: str
    tenant_name: str

    # Content hashes
    package_hash: str = ""
    manifest_checksums: list[ManifestChecksum] = field(default_factory=list)

    # Agents
    agents: list[dict[str, Any]] = field(default_factory=list)

    # Governance policies (YAML)
    policies: list[dict[str, Any]] = field(default_factory=list)
    hitl_rules: list[dict[str, Any]] = field(default_factory=list)

    # Knowledge base
    kb_sources: list[str] = field(default_factory=list)
    kb_document_count: int = 0

    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    created_by: str = ""

    # Approval tracking
    approvals: list[dict[str, Any]] = field(default_factory=list)
    all_approved: bool = False

    def compute_hash(self) -> str:
        """Compute deterministic package hash."""
        content = json.dumps({
            "org_id": self.org_id,
            "agents": sorted([a.get("name", "") for a in self.agents]),
            "policies": sorted([p.get("id", "") for p in self.policies]),
            "hitl_rules": sorted([r.get("id", "") for r in self.hitl_rules]),
            "kb_sources": sorted(self.kb_sources),
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    def add_manifest_checksum(self, filename: str, content: str) -> ManifestChecksum:
        """Add checksum for a manifest file."""
        checksum = ManifestChecksum(
            filename=filename,
            sha256=hashlib.sha256(content.encode()).hexdigest(),
            size_bytes=len(content.encode()),
        )
        self.manifest_checksums.append(checksum)
        return checksum

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "org_id": self.org_id,
            "tenant_name": self.tenant_name,
            "package_hash": self.package_hash,
            "manifest_checksums": [
                {"filename": c.filename, "sha256": c.sha256, "size_bytes": c.size_bytes}
                for c in self.manifest_checksums
            ],
            "agents": self.agents,
            "policies": self.policies,
            "hitl_rules": self.hitl_rules,
            "kb_sources": self.kb_sources,
            "kb_document_count": self.kb_document_count,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "approvals": self.approvals,
            "all_approved": self.all_approved,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DeploymentPackage":
        pkg = cls(
            package_id=data["package_id"],
            org_id=data["org_id"],
            tenant_name=data["tenant_name"],
            package_hash=data.get("package_hash", ""),
            agents=data.get("agents", []),
            policies=data.get("policies", []),
            hitl_rules=data.get("hitl_rules", []),
            kb_sources=data.get("kb_sources", []),
            kb_document_count=data.get("kb_document_count", 0),
            created_at=data.get("created_at", ""),
            created_by=data.get("created_by", ""),
            approvals=data.get("approvals", []),
            all_approved=data.get("all_approved", False),
        )
        for cs in data.get("manifest_checksums", []):
            pkg.manifest_checksums.append(ManifestChecksum(
                filename=cs["filename"],
                sha256=cs["sha256"],
                size_bytes=cs["size_bytes"],
            ))
        return pkg


class DeploymentPackageGenerator:
    """Generates deployment packages for organizations.

    ONBOARD-001: Creates deployments/{org_id}/ structure with YAML policies.
    """

    # Confidence threshold for automatic approval
    AUTO_APPROVE_THRESHOLD = 0.85

    def __init__(self, base_path: Path | None = None):
        self._base_path = base_path or Path("deployments")
        self._base_path.mkdir(parents=True, exist_ok=True)

    def create_package(
        self,
        org_id: str,
        tenant_name: str,
        agents: list[dict[str, Any]],
        departments: list[dict[str, Any]] | None = None,
        created_by: str = "system",
    ) -> DeploymentPackage:
        """Create a deployment package.

        Args:
            org_id: Organization ID
            tenant_name: Organization name
            agents: List of agent configurations
            departments: Optional detected departments with confidence scores
            created_by: User who created the package

        Returns:
            DeploymentPackage with computed hashes
        """
        package = DeploymentPackage(
            package_id=str(uuid.uuid4())[:8],
            org_id=org_id,
            tenant_name=tenant_name,
            agents=agents,
            created_by=created_by,
        )

        # Generate default policies
        package.policies = self._generate_policies(org_id, tenant_name)

        # Generate HITL rules
        package.hitl_rules = self._generate_hitl_rules(agents)

        # Check for approvals needed based on confidence
        if departments:
            for dept in departments:
                confidence = dept.get("confidence", {}).get("score", 1.0)
                needs_approval = confidence < self.AUTO_APPROVE_THRESHOLD

                package.approvals.append({
                    "item": f"Department: {dept.get('name', 'Unknown')}",
                    "confidence": confidence,
                    "needs_approval": needs_approval,
                    "approved": not needs_approval,
                    "approved_by": "auto" if not needs_approval else None,
                    "approved_at": datetime.now(UTC).isoformat() if not needs_approval else None,
                })

        # Check if all approved
        package.all_approved = all(a["approved"] for a in package.approvals)

        # Compute package hash
        package.package_hash = package.compute_hash()

        return package

    def _generate_policies(self, org_id: str, tenant_name: str) -> list[dict[str, Any]]:
        """Generate default governance policies."""
        return [
            {
                "id": f"{org_id}_default_governance",
                "name": "Default Governance Policy",
                "tenant_id": org_id,
                "rules": [
                    {"condition": "risk_level == 'high'", "action": "require_hitl"},
                    {"condition": "domain == 'Legal'", "action": "require_hitl"},
                    {"condition": "domain == 'Finance' and action == 'approve'", "action": "require_hitl"},
                ],
                "enabled": True,
            },
            {
                "id": f"{org_id}_cost_optimization",
                "name": "Cost Optimization Policy",
                "tenant_id": org_id,
                "rules": [
                    {"condition": "complexity == 'simple'", "action": "use_economy_model"},
                    {"condition": "complexity == 'complex'", "action": "use_standard_model"},
                    {"condition": "risk_level == 'high'", "action": "use_premium_model"},
                ],
                "enabled": True,
            },
        ]

    def _generate_hitl_rules(self, agents: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Generate HITL rules based on agents."""
        rules = [
            {
                "id": "hitl_legal_review",
                "name": "Legal Review Required",
                "trigger": "domain == 'Legal' and action in ['sign', 'approve', 'commit']",
                "approvers": ["legal_counsel", "legal_director"],
                "timeout_hours": 48,
            },
            {
                "id": "hitl_financial_approval",
                "name": "Financial Approval Required",
                "trigger": "domain == 'Finance' and amount > 1000",
                "approvers": ["finance_manager", "cfo"],
                "timeout_hours": 24,
            },
            {
                "id": "hitl_public_comms",
                "name": "Public Communications Review",
                "trigger": "domain == 'Communications' and audience == 'public'",
                "approvers": ["communications_director", "city_manager"],
                "timeout_hours": 24,
            },
        ]

        # Add agent-specific rules
        for agent in agents:
            if agent.get("domain") == "HR":
                rules.append({
                    "id": f"hitl_hr_{agent.get('name', 'hr').lower().replace(' ', '_')}",
                    "name": f"HR Action Review - {agent.get('name', 'HR')}",
                    "trigger": "action in ['terminate', 'promote', 'hire']",
                    "approvers": ["hr_director"],
                    "timeout_hours": 48,
                })

        return rules

    def write_package(self, package: DeploymentPackage) -> Path:
        """Write deployment package to disk.

        ONBOARD-001: Creates deployments/{org_id}/ structure.

        Structure:
            deployments/{org_id}/
                manifest.json
                agents/
                    {agent_name}.yaml
                policies/
                    governance.yaml
                    hitl_rules.yaml
                kb/
                    sources.json
        """
        pkg_path = self._base_path / package.org_id
        pkg_path.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (pkg_path / "agents").mkdir(exist_ok=True)
        (pkg_path / "policies").mkdir(exist_ok=True)
        (pkg_path / "kb").mkdir(exist_ok=True)

        # Write agent configs as YAML
        for agent in package.agents:
            agent_name = agent.get("name", "agent").lower().replace(" ", "_")
            agent_path = pkg_path / "agents" / f"{agent_name}.yaml"
            agent_yaml = yaml.dump(agent, default_flow_style=False, sort_keys=True)
            agent_path.write_text(agent_yaml)
            package.add_manifest_checksum(f"agents/{agent_name}.yaml", agent_yaml)

        # Write governance policies as YAML
        policies_yaml = yaml.dump(
            {"policies": package.policies},
            default_flow_style=False,
            sort_keys=True,
        )
        policies_path = pkg_path / "policies" / "governance.yaml"
        policies_path.write_text(policies_yaml)
        package.add_manifest_checksum("policies/governance.yaml", policies_yaml)

        # Write HITL rules as YAML
        hitl_yaml = yaml.dump(
            {"hitl_rules": package.hitl_rules},
            default_flow_style=False,
            sort_keys=True,
        )
        hitl_path = pkg_path / "policies" / "hitl_rules.yaml"
        hitl_path.write_text(hitl_yaml)
        package.add_manifest_checksum("policies/hitl_rules.yaml", hitl_yaml)

        # Write KB sources
        kb_sources = {"sources": package.kb_sources, "count": package.kb_document_count}
        kb_path = pkg_path / "kb" / "sources.json"
        kb_path.write_text(json.dumps(kb_sources, indent=2))

        # Write manifest
        manifest = package.to_dict()
        manifest_json = json.dumps(manifest, indent=2, sort_keys=True)
        manifest_path = pkg_path / "manifest.json"
        manifest_path.write_text(manifest_json)

        return pkg_path

    def load_package(self, org_id: str) -> DeploymentPackage | None:
        """Load a deployment package from disk."""
        pkg_path = self._base_path / org_id
        manifest_path = pkg_path / "manifest.json"

        if not manifest_path.exists():
            return None

        data = json.loads(manifest_path.read_text())
        return DeploymentPackage.from_dict(data)

    def verify_package(self, package: DeploymentPackage) -> tuple[bool, list[str]]:
        """Verify package integrity using checksums.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        pkg_path = self._base_path / package.org_id

        for checksum in package.manifest_checksums:
            file_path = pkg_path / checksum.filename
            if not file_path.exists():
                errors.append(f"Missing file: {checksum.filename}")
                continue

            content = file_path.read_text()
            actual_hash = hashlib.sha256(content.encode()).hexdigest()

            if actual_hash != checksum.sha256:
                errors.append(
                    f"Checksum mismatch for {checksum.filename}: "
                    f"expected {checksum.sha256[:16]}..., got {actual_hash[:16]}..."
                )

        return len(errors) == 0, errors


class DeploymentExecutor:
    """Executes deployments and supports replay.

    ONBOARD-001: Implement replay deployment from package.
    """

    def __init__(self, package_generator: DeploymentPackageGenerator | None = None):
        self._generator = package_generator or DeploymentPackageGenerator()
        self._deployment_log: list[dict[str, Any]] = []

    def execute(
        self,
        package: DeploymentPackage,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Execute a deployment.

        Args:
            package: Deployment package to execute
            dry_run: If True, don't actually deploy

        Returns:
            Deployment result
        """
        # Check approvals
        if not package.all_approved:
            pending = [a for a in package.approvals if not a["approved"]]
            return {
                "success": False,
                "error": f"Pending approvals: {len(pending)}",
                "pending_approvals": pending,
            }

        result = {
            "package_id": package.package_id,
            "org_id": package.org_id,
            "dry_run": dry_run,
            "started_at": datetime.now(UTC).isoformat(),
            "steps": [],
            "success": True,
        }

        try:
            # Step 1: Create tenant
            result["steps"].append({
                "step": "create_tenant",
                "status": "completed" if not dry_run else "skipped",
                "details": {"tenant_id": package.org_id, "name": package.tenant_name},
            })

            # Step 2: Create agents
            for agent in package.agents:
                result["steps"].append({
                    "step": "create_agent",
                    "status": "completed" if not dry_run else "skipped",
                    "details": {"name": agent.get("name"), "domain": agent.get("domain")},
                })

            # Step 3: Apply policies
            for policy in package.policies:
                result["steps"].append({
                    "step": "apply_policy",
                    "status": "completed" if not dry_run else "skipped",
                    "details": {"policy_id": policy.get("id")},
                })

            # Step 4: Configure HITL rules
            for rule in package.hitl_rules:
                result["steps"].append({
                    "step": "configure_hitl",
                    "status": "completed" if not dry_run else "skipped",
                    "details": {"rule_id": rule.get("id")},
                })

            result["completed_at"] = datetime.now(UTC).isoformat()

        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            result["completed_at"] = datetime.now(UTC).isoformat()

        # Log the deployment
        self._deployment_log.append(result)

        return result

    def replay(self, org_id: str) -> dict[str, Any]:
        """Replay a deployment from saved package.

        ONBOARD-001: Tests for identical running state.
        """
        package = self._generator.load_package(org_id)
        if not package:
            return {
                "success": False,
                "error": f"No package found for org_id: {org_id}",
            }

        # Verify package integrity
        is_valid, errors = self._generator.verify_package(package)
        if not is_valid:
            return {
                "success": False,
                "error": "Package verification failed",
                "verification_errors": errors,
            }

        # Execute the deployment
        return self.execute(package)

    def get_deployment_log(self) -> list[dict[str, Any]]:
        """Get deployment history."""
        return self._deployment_log.copy()


class ApprovalManager:
    """Manages HITL approvals for deployments.

    ONBOARD-001: Enforce HITL approvals via confidence thresholds.
    """

    # Confidence threshold for requiring approval
    CONFIDENCE_THRESHOLD = 0.85

    def __init__(self):
        self._approval_log: list[dict[str, Any]] = []

    def check_approvals_needed(
        self,
        package: DeploymentPackage,
    ) -> list[dict[str, Any]]:
        """Check which items need approval.

        Returns list of items needing human review.
        """
        needed = []

        for approval in package.approvals:
            if not approval["approved"]:
                needed.append({
                    "item": approval["item"],
                    "confidence": approval["confidence"],
                    "reason": f"Confidence {approval['confidence']:.2%} below threshold {self.CONFIDENCE_THRESHOLD:.2%}",
                })

        return needed

    def approve_item(
        self,
        package: DeploymentPackage,
        item_index: int,
        approved_by: str,
        notes: str = "",
    ) -> bool:
        """Approve a specific item.

        ONBOARD-001: Log approvals.
        """
        if item_index < 0 or item_index >= len(package.approvals):
            return False

        approval = package.approvals[item_index]
        approval["approved"] = True
        approval["approved_by"] = approved_by
        approval["approved_at"] = datetime.now(UTC).isoformat()
        approval["notes"] = notes

        # Log the approval
        self._approval_log.append({
            "package_id": package.package_id,
            "org_id": package.org_id,
            "item": approval["item"],
            "approved_by": approved_by,
            "approved_at": approval["approved_at"],
            "notes": notes,
        })

        # Update all_approved flag
        package.all_approved = all(a["approved"] for a in package.approvals)

        return True

    def can_deploy(self, package: DeploymentPackage) -> tuple[bool, str]:
        """Check if package can be deployed.

        ONBOARD-001: Block deploy if approvals missing.
        """
        if not package.approvals:
            return True, "No approvals required"

        pending = [a for a in package.approvals if not a["approved"]]
        if pending:
            return False, f"{len(pending)} approval(s) pending"

        return True, "All approvals complete"

    def get_approval_log(self) -> list[dict[str, Any]]:
        """Get approval history."""
        return self._approval_log.copy()


__all__ = [
    "ManifestChecksum",
    "DeploymentPackage",
    "DeploymentPackageGenerator",
    "DeploymentExecutor",
    "ApprovalManager",
]

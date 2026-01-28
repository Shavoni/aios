"""Auto-Onboarding Wizard with One-Click Deploy.

Provides complete onboarding workflow:
- URL discovery and analysis
- Template matching with confidence scoring
- Preview and customization
- One-click deployment
- Progress tracking
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from pathlib import Path
from typing import Any, Callable
import asyncio


class WizardStep(str, Enum):
    """Onboarding wizard steps."""

    INIT = "init"
    DISCOVERY = "discovery"
    ANALYSIS = "analysis"
    TEMPLATE_MATCH = "template_match"
    CUSTOMIZATION = "customization"
    PREVIEW = "preview"
    DEPLOYMENT = "deployment"
    COMPLETE = "complete"
    ERROR = "error"


class ConfidenceLevel(str, Enum):
    """Confidence levels for auto-detection."""

    HIGH = "high"  # > 85%
    MEDIUM = "medium"  # 60-85%
    LOW = "low"  # 40-60%
    VERY_LOW = "very_low"  # < 40%

    @classmethod
    def from_score(cls, score: float) -> ConfidenceLevel:
        if score >= 0.85:
            return cls.HIGH
        elif score >= 0.60:
            return cls.MEDIUM
        elif score >= 0.40:
            return cls.LOW
        return cls.VERY_LOW


@dataclass
class ConfidenceScore:
    """Confidence score for a detection."""

    score: float  # 0.0 - 1.0
    level: ConfidenceLevel = field(init=False)
    reason: str = ""
    evidence: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.level = ConfidenceLevel.from_score(self.score)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "level": self.level.value,
            "reason": self.reason,
            "evidence": self.evidence,
        }


@dataclass
class DetectedDepartment:
    """A detected department from discovery."""

    name: str
    url: str
    description: str = ""
    confidence: ConfidenceScore = field(default_factory=lambda: ConfidenceScore(0.5))

    # Suggested agent config
    suggested_domain: str = ""
    suggested_capabilities: list[str] = field(default_factory=list)
    suggested_model: str = "gpt-4o-mini"

    # User overrides
    enabled: bool = True
    custom_name: str = ""
    custom_instructions: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "url": self.url,
            "description": self.description,
            "confidence": self.confidence.to_dict(),
            "suggested_domain": self.suggested_domain,
            "suggested_capabilities": self.suggested_capabilities,
            "suggested_model": self.suggested_model,
            "enabled": self.enabled,
            "custom_name": self.custom_name,
            "custom_instructions": self.custom_instructions,
        }


@dataclass
class TemplateMatch:
    """A matched template with confidence."""

    template_id: str
    template_name: str
    confidence: ConfidenceScore
    modifications_needed: list[str] = field(default_factory=list)
    preview_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "template_name": self.template_name,
            "confidence": self.confidence.to_dict(),
            "modifications_needed": self.modifications_needed,
            "preview_url": self.preview_url,
        }


@dataclass
class DeploymentPreview:
    """Preview of what will be deployed."""

    tenant_id: str
    tenant_name: str

    # Agents to create
    agents: list[dict[str, Any]] = field(default_factory=list)
    agent_count: int = 0

    # Knowledge base
    kb_documents: int = 0
    kb_sources: list[str] = field(default_factory=list)

    # Governance
    policies: list[str] = field(default_factory=list)
    hitl_rules: list[str] = field(default_factory=list)

    # Estimated costs
    estimated_monthly_cost: float = 0.0
    estimated_setup_time_minutes: int = 0

    # Warnings
    warnings: list[str] = field(default_factory=list)
    requires_review: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "tenant_name": self.tenant_name,
            "agents": self.agents,
            "agent_count": self.agent_count,
            "kb_documents": self.kb_documents,
            "kb_sources": self.kb_sources,
            "policies": self.policies,
            "hitl_rules": self.hitl_rules,
            "estimated_monthly_cost": self.estimated_monthly_cost,
            "estimated_setup_time_minutes": self.estimated_setup_time_minutes,
            "warnings": self.warnings,
            "requires_review": self.requires_review,
        }


@dataclass
class WizardState:
    """Current state of the onboarding wizard."""

    id: str
    tenant_id: str
    step: WizardStep = WizardStep.INIT
    progress: float = 0.0  # 0-100%

    # Input
    organization_name: str = ""
    website_url: str = ""
    organization_type: str = "municipal"  # municipal, enterprise, nonprofit

    # Discovery results
    discovered_departments: list[DetectedDepartment] = field(default_factory=list)
    data_portals: list[str] = field(default_factory=list)
    total_pages_scanned: int = 0

    # Template matching
    matched_templates: list[TemplateMatch] = field(default_factory=list)
    selected_template: str = ""

    # Preview
    preview: DeploymentPreview | None = None

    # Deployment
    deployment_id: str = ""
    deployment_status: str = ""
    deployment_errors: list[str] = field(default_factory=list)

    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    completed_at: str = ""

    # HITL checklist
    requires_approval: bool = False
    approval_checklist: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "step": self.step.value,
            "progress": self.progress,
            "organization_name": self.organization_name,
            "website_url": self.website_url,
            "organization_type": self.organization_type,
            "discovered_departments": [d.to_dict() for d in self.discovered_departments],
            "data_portals": self.data_portals,
            "total_pages_scanned": self.total_pages_scanned,
            "matched_templates": [t.to_dict() for t in self.matched_templates],
            "selected_template": self.selected_template,
            "preview": self.preview.to_dict() if self.preview else None,
            "deployment_id": self.deployment_id,
            "deployment_status": self.deployment_status,
            "deployment_errors": self.deployment_errors,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "requires_approval": self.requires_approval,
            "approval_checklist": self.approval_checklist,
        }


class OnboardingWizard:
    """Auto-onboarding wizard with one-click deploy."""

    def __init__(self, storage_path: Path | None = None):
        self._storage_path = storage_path or Path("data/onboarding")
        self._storage_path.mkdir(parents=True, exist_ok=True)

        self._active_wizards: dict[str, WizardState] = {}
        self._load_wizards()

    def _load_wizards(self) -> None:
        """Load active wizard states."""
        for wizard_file in self._storage_path.glob("wizard_*.json"):
            try:
                data = json.loads(wizard_file.read_text())
                state = self._dict_to_state(data)
                if state.step not in (WizardStep.COMPLETE, WizardStep.ERROR):
                    self._active_wizards[state.id] = state
            except Exception:
                continue

    def _save_wizard(self, state: WizardState) -> None:
        """Save wizard state."""
        state.updated_at = datetime.now(UTC).isoformat()
        wizard_file = self._storage_path / f"wizard_{state.id}.json"
        wizard_file.write_text(json.dumps(state.to_dict(), indent=2))

    def _dict_to_state(self, data: dict[str, Any]) -> WizardState:
        """Convert dict to WizardState."""
        state = WizardState(
            id=data["id"],
            tenant_id=data["tenant_id"],
            step=WizardStep(data.get("step", "init")),
            progress=data.get("progress", 0),
            organization_name=data.get("organization_name", ""),
            website_url=data.get("website_url", ""),
            organization_type=data.get("organization_type", "municipal"),
            data_portals=data.get("data_portals", []),
            total_pages_scanned=data.get("total_pages_scanned", 0),
            selected_template=data.get("selected_template", ""),
            deployment_id=data.get("deployment_id", ""),
            deployment_status=data.get("deployment_status", ""),
            deployment_errors=data.get("deployment_errors", []),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            completed_at=data.get("completed_at", ""),
            requires_approval=data.get("requires_approval", False),
            approval_checklist=data.get("approval_checklist", []),
        )

        # Parse departments
        for dept_data in data.get("discovered_departments", []):
            conf = dept_data.get("confidence", {})
            state.discovered_departments.append(DetectedDepartment(
                name=dept_data["name"],
                url=dept_data.get("url", ""),
                description=dept_data.get("description", ""),
                confidence=ConfidenceScore(
                    score=conf.get("score", 0.5),
                    reason=conf.get("reason", ""),
                    evidence=conf.get("evidence", []),
                ),
                suggested_domain=dept_data.get("suggested_domain", ""),
                suggested_capabilities=dept_data.get("suggested_capabilities", []),
                enabled=dept_data.get("enabled", True),
            ))

        # Parse templates
        for tmpl_data in data.get("matched_templates", []):
            conf = tmpl_data.get("confidence", {})
            state.matched_templates.append(TemplateMatch(
                template_id=tmpl_data["template_id"],
                template_name=tmpl_data["template_name"],
                confidence=ConfidenceScore(
                    score=conf.get("score", 0.5),
                    reason=conf.get("reason", ""),
                ),
                modifications_needed=tmpl_data.get("modifications_needed", []),
            ))

        # Parse preview
        if data.get("preview"):
            p = data["preview"]
            state.preview = DeploymentPreview(
                tenant_id=p["tenant_id"],
                tenant_name=p["tenant_name"],
                agents=p.get("agents", []),
                agent_count=p.get("agent_count", 0),
                kb_documents=p.get("kb_documents", 0),
                kb_sources=p.get("kb_sources", []),
                policies=p.get("policies", []),
                hitl_rules=p.get("hitl_rules", []),
                estimated_monthly_cost=p.get("estimated_monthly_cost", 0),
                estimated_setup_time_minutes=p.get("estimated_setup_time_minutes", 0),
                warnings=p.get("warnings", []),
                requires_review=p.get("requires_review", []),
            )

        return state

    # =========================================================================
    # Wizard Lifecycle
    # =========================================================================

    def start_wizard(
        self,
        organization_name: str,
        website_url: str,
        organization_type: str = "municipal",
        tenant_id: str | None = None,
    ) -> WizardState:
        """Start a new onboarding wizard."""
        wizard_id = str(uuid.uuid4())[:8]
        tenant_id = tenant_id or f"tenant_{wizard_id}"

        state = WizardState(
            id=wizard_id,
            tenant_id=tenant_id,
            organization_name=organization_name,
            website_url=website_url,
            organization_type=organization_type,
            step=WizardStep.INIT,
            progress=5.0,
        )

        self._active_wizards[wizard_id] = state
        self._save_wizard(state)

        return state

    def get_wizard(self, wizard_id: str) -> WizardState | None:
        """Get wizard state by ID."""
        if wizard_id in self._active_wizards:
            return self._active_wizards[wizard_id]

        # Try loading from disk
        wizard_file = self._storage_path / f"wizard_{wizard_id}.json"
        if wizard_file.exists():
            data = json.loads(wizard_file.read_text())
            return self._dict_to_state(data)

        return None

    def list_wizards(self, include_completed: bool = False) -> list[dict[str, Any]]:
        """List all wizard states."""
        results = []
        for wizard_file in self._storage_path.glob("wizard_*.json"):
            try:
                data = json.loads(wizard_file.read_text())
                if not include_completed and data.get("step") in ("complete", "error"):
                    continue
                results.append({
                    "id": data["id"],
                    "organization_name": data.get("organization_name", ""),
                    "step": data.get("step", ""),
                    "progress": data.get("progress", 0),
                    "created_at": data.get("created_at", ""),
                })
            except Exception:
                continue
        return sorted(results, key=lambda x: x["created_at"], reverse=True)

    # =========================================================================
    # Step: Discovery
    # =========================================================================

    async def run_discovery(self, wizard_id: str) -> WizardState:
        """Run URL discovery for the organization."""
        state = self.get_wizard(wizard_id)
        if not state:
            raise ValueError(f"Wizard {wizard_id} not found")

        state.step = WizardStep.DISCOVERY
        state.progress = 10.0
        self._save_wizard(state)

        try:
            # Import discovery engine
            from packages.onboarding.discovery import DiscoveryEngine

            engine = DiscoveryEngine()
            result = await engine.discover(state.website_url)

            # Convert to detected departments
            for dept in result.departments:
                confidence = ConfidenceScore(
                    score=0.7 if dept.url else 0.4,
                    reason="Detected from website structure",
                    evidence=[f"Found at {dept.url}"] if dept.url else [],
                )

                state.discovered_departments.append(DetectedDepartment(
                    name=dept.name,
                    url=dept.url or "",
                    description=dept.description or "",
                    confidence=confidence,
                    suggested_domain=self._infer_domain(dept.name),
                    suggested_capabilities=self._infer_capabilities(dept.name),
                ))

            state.data_portals = [dp.url for dp in result.data_portals] if hasattr(result, 'data_portals') else []
            state.total_pages_scanned = result.pages_scanned if hasattr(result, 'pages_scanned') else 0

            state.step = WizardStep.ANALYSIS
            state.progress = 30.0

        except Exception as e:
            state.step = WizardStep.ERROR
            state.deployment_errors.append(f"Discovery failed: {str(e)}")

        self._save_wizard(state)
        return state

    def _infer_domain(self, name: str) -> str:
        """Infer domain from department name."""
        name_lower = name.lower()
        domain_keywords = {
            "HR": ["hr", "human resource", "personnel", "employee"],
            "Finance": ["finance", "budget", "treasury", "accounting"],
            "Legal": ["legal", "law", "attorney", "counsel"],
            "Building": ["building", "permit", "zoning", "planning"],
            "PublicHealth": ["health", "medical", "clinic"],
            "PublicSafety": ["police", "fire", "safety", "emergency"],
            "Parks": ["parks", "recreation", "community"],
            "Utilities": ["water", "utilities", "electric", "sewer"],
        }

        for domain, keywords in domain_keywords.items():
            if any(kw in name_lower for kw in keywords):
                return domain

        return "General"

    def _infer_capabilities(self, name: str) -> list[str]:
        """Infer capabilities from department name."""
        name_lower = name.lower()
        capabilities = []

        if any(kw in name_lower for kw in ["hr", "human"]):
            capabilities = ["benefits", "policies", "onboarding", "leave"]
        elif any(kw in name_lower for kw in ["finance", "budget"]):
            capabilities = ["budgets", "payments", "procurement", "reporting"]
        elif any(kw in name_lower for kw in ["legal"]):
            capabilities = ["contracts", "compliance", "records"]
        elif any(kw in name_lower for kw in ["building", "permit"]):
            capabilities = ["permits", "inspections", "zoning", "codes"]

        return capabilities or ["general inquiry", "information"]

    # =========================================================================
    # Step: Template Matching
    # =========================================================================

    def match_templates(self, wizard_id: str) -> WizardState:
        """Match organization to available templates."""
        state = self.get_wizard(wizard_id)
        if not state:
            raise ValueError(f"Wizard {wizard_id} not found")

        state.step = WizardStep.TEMPLATE_MATCH
        state.progress = 50.0

        # Load available templates
        templates_path = Path("templates")
        available_templates = []

        for template_dir in templates_path.iterdir():
            if template_dir.is_dir():
                manifest_file = template_dir / "manifest.json"
                if manifest_file.exists():
                    manifest = json.loads(manifest_file.read_text())
                    available_templates.append({
                        "id": template_dir.name,
                        "name": manifest.get("name", template_dir.name),
                        "type": manifest.get("type", "generic"),
                        "agents": manifest.get("agents", []),
                    })

        # Score each template
        for template in available_templates:
            score = self._score_template_match(state, template)
            state.matched_templates.append(TemplateMatch(
                template_id=template["id"],
                template_name=template["name"],
                confidence=score,
                modifications_needed=self._get_modifications_needed(state, template),
            ))

        # Sort by confidence
        state.matched_templates.sort(key=lambda t: t.confidence.score, reverse=True)

        # Auto-select best match if high confidence
        if state.matched_templates and state.matched_templates[0].confidence.level == ConfidenceLevel.HIGH:
            state.selected_template = state.matched_templates[0].template_id

        state.step = WizardStep.CUSTOMIZATION
        state.progress = 60.0

        self._save_wizard(state)
        return state

    def _score_template_match(self, state: WizardState, template: dict) -> ConfidenceScore:
        """Score how well a template matches the organization."""
        score = 0.5
        evidence = []

        # Type match
        if template.get("type") == state.organization_type:
            score += 0.2
            evidence.append(f"Organization type matches: {state.organization_type}")

        # Department coverage
        template_domains = {a.get("domain", "") for a in template.get("agents", [])}
        org_domains = {d.suggested_domain for d in state.discovered_departments}

        overlap = len(template_domains & org_domains)
        if overlap > 0:
            coverage = overlap / max(len(org_domains), 1)
            score += coverage * 0.3
            evidence.append(f"{overlap} domain(s) match template")

        return ConfidenceScore(
            score=min(score, 1.0),
            reason=f"Template match for {state.organization_type}",
            evidence=evidence,
        )

    def _get_modifications_needed(self, state: WizardState, template: dict) -> list[str]:
        """Identify modifications needed for a template."""
        mods = []

        template_domains = {a.get("domain", "") for a in template.get("agents", [])}
        org_domains = {d.suggested_domain for d in state.discovered_departments}

        # Missing agents
        missing = org_domains - template_domains
        if missing:
            mods.append(f"Add agents for: {', '.join(missing)}")

        # Extra agents
        extra = template_domains - org_domains
        if extra:
            mods.append(f"Remove unused agents: {', '.join(extra)}")

        return mods

    # =========================================================================
    # Step: Customization
    # =========================================================================

    def update_department(
        self,
        wizard_id: str,
        department_name: str,
        enabled: bool | None = None,
        custom_name: str | None = None,
        custom_instructions: str | None = None,
    ) -> WizardState:
        """Update department configuration."""
        state = self.get_wizard(wizard_id)
        if not state:
            raise ValueError(f"Wizard {wizard_id} not found")

        for dept in state.discovered_departments:
            if dept.name == department_name:
                if enabled is not None:
                    dept.enabled = enabled
                if custom_name is not None:
                    dept.custom_name = custom_name
                if custom_instructions is not None:
                    dept.custom_instructions = custom_instructions
                break

        self._save_wizard(state)
        return state

    def select_template(self, wizard_id: str, template_id: str) -> WizardState:
        """Select a template for deployment."""
        state = self.get_wizard(wizard_id)
        if not state:
            raise ValueError(f"Wizard {wizard_id} not found")

        state.selected_template = template_id
        self._save_wizard(state)

        return state

    # =========================================================================
    # Step: Preview
    # =========================================================================

    def generate_preview(self, wizard_id: str) -> WizardState:
        """Generate deployment preview."""
        state = self.get_wizard(wizard_id)
        if not state:
            raise ValueError(f"Wizard {wizard_id} not found")

        state.step = WizardStep.PREVIEW
        state.progress = 75.0

        # Build preview
        enabled_depts = [d for d in state.discovered_departments if d.enabled]

        agents = []
        for dept in enabled_depts:
            agents.append({
                "name": dept.custom_name or dept.name,
                "domain": dept.suggested_domain,
                "capabilities": dept.suggested_capabilities,
                "model": dept.suggested_model,
                "confidence": dept.confidence.score,
            })

        # Add concierge
        agents.insert(0, {
            "name": "Concierge",
            "domain": "Router",
            "capabilities": ["routing", "general inquiry"],
            "model": "gpt-4o",
            "is_router": True,
        })

        # Estimate costs
        base_cost = 50.0  # Base platform
        per_agent_cost = 15.0
        estimated_cost = base_cost + (len(agents) * per_agent_cost)

        # Check for items requiring review
        requires_review = []
        warnings = []

        low_confidence = [d for d in enabled_depts if d.confidence.level in (ConfidenceLevel.LOW, ConfidenceLevel.VERY_LOW)]
        if low_confidence:
            requires_review.append(f"{len(low_confidence)} department(s) have low detection confidence")

        if len(agents) > 10:
            warnings.append("Large number of agents may increase costs and complexity")

        state.preview = DeploymentPreview(
            tenant_id=state.tenant_id,
            tenant_name=state.organization_name,
            agents=agents,
            agent_count=len(agents),
            kb_documents=len(enabled_depts) * 15,  # Estimate
            kb_sources=[d.url for d in enabled_depts if d.url],
            policies=["default_governance", "hitl_legal", "hitl_finance"],
            hitl_rules=["legal_review", "financial_approval", "public_comms"],
            estimated_monthly_cost=estimated_cost,
            estimated_setup_time_minutes=5 + (len(agents) * 2),
            warnings=warnings,
            requires_review=requires_review,
        )

        # Check if HITL approval needed
        state.requires_approval = len(requires_review) > 0
        if state.requires_approval:
            state.approval_checklist = [
                {"item": item, "approved": False} for item in requires_review
            ]

        self._save_wizard(state)
        return state

    # =========================================================================
    # Step: One-Click Deploy
    # =========================================================================

    async def deploy(self, wizard_id: str, skip_approval: bool = False) -> WizardState:
        """Execute one-click deployment."""
        state = self.get_wizard(wizard_id)
        if not state:
            raise ValueError(f"Wizard {wizard_id} not found")

        # Check approvals
        if state.requires_approval and not skip_approval:
            pending = [c for c in state.approval_checklist if not c.get("approved")]
            if pending:
                raise ValueError(f"Deployment requires approval: {len(pending)} item(s) pending")

        state.step = WizardStep.DEPLOYMENT
        state.progress = 85.0
        state.deployment_status = "starting"
        self._save_wizard(state)

        try:
            # Generate deployment ID
            state.deployment_id = str(uuid.uuid4())[:8]

            # 1. Create tenant
            state.deployment_status = "creating_tenant"
            state.progress = 88.0
            self._save_wizard(state)

            from packages.core.multitenancy import get_tenant_manager, TenantTier
            tenant_mgr = get_tenant_manager()
            tenant = tenant_mgr.create_tenant(
                name=state.organization_name,
                tier=TenantTier.PROFESSIONAL,
            )

            # 2. Create agents
            state.deployment_status = "creating_agents"
            state.progress = 92.0
            self._save_wizard(state)

            from packages.core.agents import get_agent_manager

            manager = get_agent_manager()
            for agent_config in state.preview.agents if state.preview else []:
                manager.create_agent(
                    name=agent_config["name"],
                    domain=agent_config["domain"],
                    capabilities=agent_config.get("capabilities", []),
                    model=agent_config.get("model", "gpt-4o-mini"),
                    is_router=agent_config.get("is_router", False),
                )

            # 3. Generate knowledge base
            state.deployment_status = "generating_kb"
            state.progress = 95.0
            self._save_wizard(state)

            # KB generation would happen here

            # 4. Apply governance policies
            state.deployment_status = "applying_policies"
            state.progress = 98.0
            self._save_wizard(state)

            # Policy application would happen here

            # Complete
            state.step = WizardStep.COMPLETE
            state.progress = 100.0
            state.deployment_status = "complete"
            state.completed_at = datetime.now(UTC).isoformat()

        except Exception as e:
            state.step = WizardStep.ERROR
            state.deployment_status = "failed"
            state.deployment_errors.append(str(e))

        self._save_wizard(state)
        return state

    def approve_checklist_item(self, wizard_id: str, item_index: int) -> WizardState:
        """Approve a checklist item."""
        state = self.get_wizard(wizard_id)
        if not state:
            raise ValueError(f"Wizard {wizard_id} not found")

        if 0 <= item_index < len(state.approval_checklist):
            state.approval_checklist[item_index]["approved"] = True

        # Check if all approved
        all_approved = all(c.get("approved") for c in state.approval_checklist)
        if all_approved:
            state.requires_approval = False

        self._save_wizard(state)
        return state


# Singleton
_wizard: OnboardingWizard | None = None


def get_wizard() -> OnboardingWizard:
    """Get the onboarding wizard singleton."""
    global _wizard
    if _wizard is None:
        _wizard = OnboardingWizard()
    return _wizard


__all__ = [
    "WizardStep",
    "ConfidenceLevel",
    "ConfidenceScore",
    "DetectedDepartment",
    "TemplateMatch",
    "DeploymentPreview",
    "WizardState",
    "OnboardingWizard",
    "get_wizard",
]

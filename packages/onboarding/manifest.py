"""Manifest Generator for deployment configurations."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from packages.onboarding.config import OnboardingConfig

# Agent templates with system prompts
AGENT_TEMPLATES = {
    "public-health": {
        "name_format": "{director_name}",
        "title_format": "Director of Public Health",
        "domain": "PublicHealth",
        "capabilities": [
            "Staff workflow creation",
            "Resident-facing drafts",
            "Public advisory translation",
            "Health communication guidance",
        ],
        "guardrails": [
            "Protect PHI (HIPAA compliance required)",
            "No clinical or medical advice",
            "Route PHI requests to privacy/legal",
            "No operational steps involving sensitive data",
        ],
        "escalates_to": "Public Health Leadership",
        "sensitivity": "high",
        "system_prompt_template": """You are {name}, {title} for {municipality}.

Your role is to help city staff with public health matters by:
- Converting approved program guidance into clear staff workflows
- Creating resident-facing communication drafts
- Translating public advisories into actionable steps
- Providing health communication guidance

IMPORTANT GUARDRAILS:
- NEVER provide clinical or medical advice
- NEVER handle or discuss Protected Health Information (PHI)
- Route any PHI-related requests to privacy/legal immediately
- Only use approved, published guidance from official sources
- When uncertain, escalate to Public Health Leadership""",
    },
    "hr": {
        "name_format": "{director_name}",
        "title_format": "HR Director",
        "domain": "HR",
        "capabilities": [
            "Policy interpretation",
            "Manager support",
            "Communication drafts",
            "Responsible AI guidance",
        ],
        "guardrails": [
            "Protect employee privacy",
            "No employment decisions",
            "Route sensitive matters to HR leadership",
            "Fairness and equity in all guidance",
        ],
        "escalates_to": "HR Leadership",
        "sensitivity": "high",
        "system_prompt_template": """You are {name}, {title} for {municipality}.

Your role is to help city staff with HR matters by:
- Interpreting HR policies clearly
- Supporting managers with people-related questions
- Drafting internal HR communications
- Providing guidance on responsible AI use

IMPORTANT GUARDRAILS:
- NEVER make employment decisions (hiring, firing, discipline)
- Protect employee privacy at all times
- Route sensitive personnel matters to HR leadership
- Ensure fairness and equity in all guidance
- Reference specific policies when providing guidance""",
    },
    "finance": {
        "name_format": "{director_name}",
        "title_format": "Chief Financial Officer",
        "domain": "Finance",
        "capabilities": [
            "Purchasing rule guidance",
            "Budget process explanation",
            "Vendor workflow support",
            "Compliant draft generation",
        ],
        "guardrails": [
            "No legal advice",
            "Flag audit risks",
            "Route exceptions to human approval",
            "Source from approved policies only",
        ],
        "escalates_to": "Finance Leadership / Procurement",
        "sensitivity": "high",
        "system_prompt_template": """You are {name}, {title} for {municipality}.

Your role is to help city staff with finance and procurement matters by:
- Explaining purchasing rules and processes
- Clarifying budget procedures
- Supporting vendor workflow questions
- Generating compliant justifications and drafts

IMPORTANT GUARDRAILS:
- NEVER provide legal advice
- Always flag potential audit risks
- Route exceptions and approvals to humans
- Only source guidance from approved city policies
- Document all guidance for audit trail""",
    },
    "building": {
        "name_format": "{director_name}",
        "title_format": "Building & Housing Director",
        "domain": "Building",
        "capabilities": [
            "Permit guidance",
            "Inspection procedures",
            "Code reference lookup",
            "Notice drafting",
        ],
        "guardrails": [
            "Use approved procedures only",
            "Reference specific codes",
            "Route complex cases to experts",
            "No legal interpretations",
        ],
        "escalates_to": "Building & Housing Leadership",
        "sensitivity": "medium",
        "system_prompt_template": """You are {name}, {title} for {municipality}.

Your role is to help city staff and residents with building and housing matters by:
- Providing permit guidance and requirements
- Explaining inspection procedures
- Looking up relevant building and housing codes
- Drafting notices and communications

IMPORTANT GUARDRAILS:
- Only use approved city procedures
- Always cite specific code sections
- Route complex or unusual cases to expert staff
- Never provide legal interpretations of code
- Encourage consultation with inspectors for edge cases""",
    },
    "311": {
        "name_format": "{director_name}",
        "title_format": "Director of 311",
        "domain": "311",
        "capabilities": [
            "Script guidance",
            "Service catalog rules",
            "Escalation path routing",
            "Knowledge article refinement",
        ],
        "guardrails": [
            "Follow service catalog",
            "Consistent response drafting",
            "Proper escalation paths",
            "No promises outside SLA",
        ],
        "escalates_to": "311 Supervisors",
        "sensitivity": "low",
        "system_prompt_template": """You are {name}, {title} for {municipality}.

Your role is to help 311 staff with citizen service matters by:
- Providing approved call scripts and guidance
- Clarifying service catalog rules and procedures
- Routing requests through proper escalation paths
- Improving knowledge articles and FAQs

IMPORTANT GUARDRAILS:
- Always follow the service catalog
- Maintain consistent response drafting
- Use established escalation paths
- Never promise response times outside SLA
- Log all interactions for quality assurance""",
    },
    "strategy": {
        "name_format": "{director_name}",
        "title_format": "Strategy Advisor",
        "domain": "Strategy",
        "capabilities": [
            "Strategic guidance",
            "Deal-making documents",
            "Pilot design",
            "Governance modeling",
        ],
        "guardrails": [
            "No commitment impersonation",
            "Source-based responses only",
            "Flag missing information",
            "Escalate political decisions",
        ],
        "escalates_to": "City Leadership",
        "sensitivity": "high",
        "system_prompt_template": """You are {name}, {title} for {municipality}.

Your role is to provide strategic guidance on AI and technology initiatives by:
- Offering strategic analysis and recommendations
- Drafting deal-making and partnership documents
- Designing pilot programs and evaluation criteria
- Modeling governance frameworks

IMPORTANT GUARDRAILS:
- Never impersonate or make commitments on behalf of leadership
- Only provide responses grounded in available sources
- Flag when information is missing or uncertain
- Escalate political and policy decisions to leadership
- Maintain confidentiality of strategic discussions""",
    },
    "public-safety": {
        "name_format": "{director_name}",
        "title_format": "Public Safety Director",
        "domain": "PublicSafety",
        "capabilities": [
            "Policy guidance",
            "Procedure clarification",
            "Report drafting",
            "Training support",
        ],
        "guardrails": [
            "No operational decisions",
            "Protect officer safety information",
            "Route active incidents to dispatch",
            "No access to criminal records",
        ],
        "escalates_to": "Public Safety Leadership",
        "sensitivity": "critical",
        "system_prompt_template": """You are {name}, {title} for {municipality}.

Your role is to help public safety staff with administrative matters by:
- Providing policy guidance
- Clarifying procedures
- Drafting reports and communications
- Supporting training initiatives

IMPORTANT GUARDRAILS:
- NEVER make operational or tactical decisions
- Protect all officer safety information
- Route any active incidents to proper dispatch
- No access to or discussion of criminal records
- Escalate any legal matters to city attorney""",
    },
    "parks": {
        "name_format": "{director_name}",
        "title_format": "Parks & Recreation Director",
        "domain": "Parks",
        "capabilities": [
            "Facility information",
            "Program guidance",
            "Reservation support",
            "Event planning assistance",
        ],
        "guardrails": [
            "Verify facility availability",
            "No fee waivers",
            "Route permit requests properly",
            "Accurate program information only",
        ],
        "escalates_to": "Parks Leadership",
        "sensitivity": "low",
        "system_prompt_template": """You are {name}, {title} for {municipality}.

Your role is to help residents and staff with parks and recreation matters by:
- Providing facility information and hours
- Explaining programs and registration
- Supporting reservation requests
- Assisting with event planning

IMPORTANT GUARDRAILS:
- Always verify facility availability before confirming
- Never grant fee waivers (route to supervisor)
- Route permit requests through proper channels
- Only provide information from approved program guides""",
    },
    "public-works": {
        "name_format": "{director_name}",
        "title_format": "Public Works Director",
        "domain": "PublicWorks",
        "capabilities": [
            "Service information",
            "Project updates",
            "Request routing",
            "Procedure guidance",
        ],
        "guardrails": [
            "No cost estimates",
            "Route emergencies to dispatch",
            "Verify project information",
            "No contractor recommendations",
        ],
        "escalates_to": "Public Works Leadership",
        "sensitivity": "medium",
        "system_prompt_template": """You are {name}, {title} for {municipality}.

Your role is to help residents and staff with public works matters by:
- Providing service information
- Sharing project updates
- Routing service requests properly
- Explaining procedures and timelines

IMPORTANT GUARDRAILS:
- Never provide cost estimates
- Route all emergencies to proper dispatch
- Verify project information before sharing
- Never recommend specific contractors
- Use official project communications only""",
    },
}


@dataclass
class AgentManifest:
    """Manifest for a single agent."""
    id: str
    name: str
    title: str
    domain: str
    description: str
    system_prompt: str
    capabilities: list[str]
    guardrails: list[str]
    escalates_to: str
    sensitivity: str
    data_source_ids: list[str] = field(default_factory=list)
    status: str = "active"


@dataclass
class ConciergeManifest:
    """Manifest for the Concierge router."""
    id: str = "concierge"
    name: str = "Civic AI Concierge"
    title: str = "Leadership Asset Router"
    domain: str = "Router"
    routing_rules: list[dict[str, Any]] = field(default_factory=list)
    system_prompt: str = ""


@dataclass
class GovernanceManifest:
    """Manifest for governance policies."""
    sensitivity_rules: dict[str, dict[str, Any]] = field(default_factory=dict)
    department_policies: dict[str, list[str]] = field(default_factory=dict)
    global_guardrails: list[str] = field(default_factory=list)


@dataclass
class DeploymentManifest:
    """Complete deployment manifest."""
    id: str
    config_id: str
    municipality_name: str
    created_at: str
    agents: list[AgentManifest] = field(default_factory=list)
    concierge: ConciergeManifest | None = None
    governance: GovernanceManifest | None = None
    data_sources: list[dict[str, Any]] = field(default_factory=list)
    sync_schedule: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "config_id": self.config_id,
            "municipality_name": self.municipality_name,
            "created_at": self.created_at,
            "agents": [
                {
                    "id": a.id,
                    "name": a.name,
                    "title": a.title,
                    "domain": a.domain,
                    "description": a.description,
                    "system_prompt": a.system_prompt,
                    "capabilities": a.capabilities,
                    "guardrails": a.guardrails,
                    "escalates_to": a.escalates_to,
                    "data_source_ids": a.data_source_ids,
                    "status": a.status,
                }
                for a in self.agents
            ],
            "concierge": {
                "id": self.concierge.id,
                "name": self.concierge.name,
                "title": self.concierge.title,
                "domain": self.concierge.domain,
                "routing_rules": self.concierge.routing_rules,
                "system_prompt": self.concierge.system_prompt,
            } if self.concierge else None,
            "governance": {
                "sensitivity_rules": self.governance.sensitivity_rules,
                "department_policies": self.governance.department_policies,
                "global_guardrails": self.governance.global_guardrails,
            } if self.governance else None,
            "data_sources": self.data_sources,
            "sync_schedule": self.sync_schedule,
        }


class ManifestGenerator:
    """Generates deployment manifests from configurations."""

    def __init__(self, storage_path: Path | None = None) -> None:
        self.storage_path = storage_path or Path("data/onboarding/manifests")
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def generate(self, config: OnboardingConfig) -> DeploymentManifest:
        """Generate a deployment manifest from configuration.

        Args:
            config: The OnboardingConfig to generate from

        Returns:
            DeploymentManifest ready for deployment
        """
        manifest_id = f"manifest-{config.id.replace('config-', '')}"
        now = datetime.utcnow().isoformat()

        manifest = DeploymentManifest(
            id=manifest_id,
            config_id=config.id,
            municipality_name=config.municipality_name,
            created_at=now,
        )

        # Generate agents for enabled departments
        for dept in config.departments:
            if not dept.enabled:
                continue

            agent = self._generate_agent(dept, config.municipality_name)
            if agent:
                manifest.agents.append(agent)

        # Generate Concierge
        manifest.concierge = self._generate_concierge(config, manifest.agents)

        # Generate governance
        manifest.governance = self._generate_governance(config, manifest.agents)

        # Add data sources
        manifest.data_sources = self._prepare_data_sources(config)

        # Set up sync schedule
        manifest.sync_schedule = {
            "default_interval_hours": config.sync.default_refresh_hours,
            "sources": {
                s.id: s.sync_frequency
                for s in config.data_sources
                if s.enabled
            },
        }

        # Save manifest
        self._save_manifest(manifest)

        return manifest

    def _generate_agent(
        self, dept: Any, municipality_name: str
    ) -> AgentManifest | None:
        """Generate an agent manifest for a department."""
        template_id = dept.template_id
        if not template_id or template_id not in AGENT_TEMPLATES:
            # Use generic template
            return AgentManifest(
                id=dept.id,
                name=dept.custom_name or dept.name,
                title=dept.director_title or "Department Director",
                domain="General",
                description=dept.custom_description or f"{dept.name} Leadership Asset",
                system_prompt=self._generic_system_prompt(dept, municipality_name),
                capabilities=["Policy guidance", "Information lookup", "Draft creation"],
                guardrails=["Verify information", "Route complex matters", "Protect privacy"],
                escalates_to=f"{dept.name} Leadership",
                sensitivity="medium",
                data_source_ids=dept.data_source_ids,
            )

        template = AGENT_TEMPLATES[template_id]

        # Build name
        name = dept.director_name or "Department AI"
        title = dept.director_title or template["title_format"]

        # Build system prompt
        system_prompt = template["system_prompt_template"].format(
            name=name,
            title=title,
            municipality=municipality_name,
        )

        return AgentManifest(
            id=dept.id,
            name=name,
            title=title,
            domain=template["domain"],
            description=dept.custom_description or f"{municipality_name} {template['title_format']}",
            system_prompt=system_prompt,
            capabilities=template["capabilities"].copy(),
            guardrails=template["guardrails"].copy(),
            escalates_to=template["escalates_to"],
            sensitivity=template["sensitivity"],
            data_source_ids=dept.data_source_ids,
        )

    def _generic_system_prompt(self, dept: Any, municipality_name: str) -> str:
        """Generate a generic system prompt for unknown department types."""
        return f"""You are the AI assistant for {dept.name} at {municipality_name}.

Your role is to help city staff with matters related to {dept.name} by:
- Providing policy guidance and information
- Drafting communications
- Answering procedural questions
- Routing complex matters appropriately

IMPORTANT GUARDRAILS:
- Only provide information from approved sources
- Route complex or sensitive matters to department leadership
- Protect confidential information
- When uncertain, acknowledge limitations and escalate"""

    def _generate_concierge(
        self, config: OnboardingConfig, agents: list[AgentManifest]
    ) -> ConciergeManifest:
        """Generate the Concierge router configuration."""
        concierge = ConciergeManifest(
            name=f"{config.municipality_name} Civic AI Concierge",
            title="Leadership Asset Router",
        )

        # Build routing rules
        for agent in agents:
            concierge.routing_rules.append({
                "agent_id": agent.id,
                "domain": agent.domain,
                "keywords": self._get_routing_keywords(agent.domain),
            })

        # Build system prompt
        agent_list = "\n".join([
            f"- **{a.name}** ({a.title}): {a.domain} domain - {', '.join(a.capabilities[:2])}"
            for a in agents
        ])

        concierge.system_prompt = f"""You are the {config.municipality_name} Civic AI Concierge.

Your role is to route city employees to the correct department leadership asset. You should:
1. Listen to the user's request
2. Identify which department can best help
3. Ask clarifying questions if needed (minimal - 1-2 max)
4. Route to the appropriate leadership asset
5. Provide safe next steps if uncertain

AVAILABLE LEADERSHIP ASSETS:
{agent_list}

ROUTING GUIDELINES:
- Be concise and efficient
- Ask minimal clarifying questions
- When in doubt, acknowledge and offer options
- Never speculate on policy
- Escalate high-risk matters to human leadership"""

        return concierge

    def _get_routing_keywords(self, domain: str) -> list[str]:
        """Get routing keywords for a domain."""
        keyword_map = {
            "PublicHealth": ["health", "clinic", "disease", "vaccine", "opioid"],
            "HR": ["hr", "employee", "benefits", "hiring", "leave"],
            "Finance": ["budget", "procurement", "vendor", "invoice", "payment"],
            "Building": ["permit", "inspection", "building", "housing", "zoning"],
            "311": ["311", "pothole", "trash", "noise", "complaint"],
            "Strategy": ["strategy", "initiative", "pilot", "partnership"],
            "PublicSafety": ["police", "safety", "crime", "security"],
            "Parks": ["park", "recreation", "facility", "program"],
            "PublicWorks": ["street", "water", "sewer", "utility"],
        }
        return keyword_map.get(domain, [domain.lower()])

    def _generate_governance(
        self, config: OnboardingConfig, agents: list[AgentManifest]
    ) -> GovernanceManifest:
        """Generate governance policies."""
        governance = GovernanceManifest()

        # Sensitivity rules
        governance.sensitivity_rules = {
            "critical": {
                "hitl_mode": "ESCALATE",
                "requires_approval": True,
                "audit_level": "detailed",
            },
            "high": {
                "hitl_mode": "DRAFT",
                "requires_approval": True,
                "audit_level": "standard",
            },
            "medium": {
                "hitl_mode": "INFORM",
                "requires_approval": False,
                "audit_level": "standard",
            },
            "low": {
                "hitl_mode": "EXECUTE",
                "requires_approval": False,
                "audit_level": "minimal",
            },
        }

        # Department policies
        for agent in agents:
            governance.department_policies[agent.id] = agent.guardrails

        # Global guardrails
        governance.global_guardrails = [
            "Never impersonate a city official",
            "Always identify as an AI assistant",
            "Protect personally identifiable information (PII)",
            "Log all interactions for audit compliance",
            "Escalate legal and safety matters to humans",
        ]

        return governance

    def _prepare_data_sources(self, config: OnboardingConfig) -> list[dict[str, Any]]:
        """Prepare data source configurations for deployment."""
        sources = []
        for ds in config.data_sources:
            if ds.enabled:
                sources.append({
                    "id": ds.id,
                    "name": ds.name,
                    "department_id": ds.department_id,
                    "api_endpoint": ds.api_endpoint,
                    "sync_frequency": ds.sync_frequency,
                })
        return sources

    def _save_manifest(self, manifest: DeploymentManifest) -> None:
        """Save manifest to storage."""
        filepath = self.storage_path / f"{manifest.id}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, indent=2)


# Module-level singleton
_manifest_generator: ManifestGenerator | None = None


def get_manifest_generator() -> ManifestGenerator:
    """Get the manifest generator singleton."""
    global _manifest_generator
    if _manifest_generator is None:
        _manifest_generator = ManifestGenerator()
    return _manifest_generator


def generate_manifest(config: OnboardingConfig) -> DeploymentManifest:
    """Generate a deployment manifest from configuration."""
    return get_manifest_generator().generate(config)

"""Agent management module for Cleveland Leadership Assets."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from datetime import datetime

from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    """Configuration for a Leadership Asset agent."""

    id: str
    name: str
    title: str
    domain: str
    description: str
    capabilities: list[str] = Field(default_factory=list)
    guardrails: list[str] = Field(default_factory=list)
    escalates_to: str = ""
    gpt_url: str = ""
    system_prompt: str = ""
    status: str = "active"  # active, inactive, degraded
    is_router: bool = False
    # Branding fields
    avatar_url: str = ""  # URL to agent's avatar/profile image
    logo_url: str = ""  # URL to department/organization logo
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class AgentManager:
    """Manages Leadership Asset agents with persistence."""

    def __init__(self, storage_path: str | None = None):
        if storage_path is None:
            storage_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", "data", "agents.json"
            )
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._agents: dict[str, AgentConfig] = {}
        self._load()

    def _load(self) -> None:
        """Load agents from storage."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path) as f:
                    data = json.load(f)
                    for agent_data in data.get("agents", []):
                        agent = AgentConfig(**agent_data)
                        self._agents[agent.id] = agent
            except Exception:
                self._agents = {}

        # Initialize with Cleveland defaults if empty
        if not self._agents:
            self._initialize_cleveland_agents()
            self._save()

    def _save(self) -> None:
        """Save agents to storage."""
        data = {"agents": [agent.model_dump() for agent in self._agents.values()]}
        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=2)

    def _initialize_cleveland_agents(self) -> None:
        """Initialize with Cleveland Leadership Assets."""
        defaults = [
            AgentConfig(
                id="concierge",
                name="Cleveland Civic AI Concierge",
                title="Leadership Asset Router",
                domain="Router",
                description="Routes staff to the correct department leadership asset. Clarifies intent with minimal questions, provides safe next steps, and escalates high-risk matters.",
                capabilities=["Intent classification", "Department routing", "Risk triage", "Safe next-step guidance"],
                guardrails=["Minimal clarifying questions", "No speculation on policy", "Escalate high-risk to human"],
                escalates_to="Department Leadership",
                gpt_url="https://chatgpt.com/g/g-693f69110450819193f6657905a2bc16-1-cleveland-civic-ai-concierge-leadership-asset",
                system_prompt="You are the Cleveland Civic AI Concierge. Your role is to route staff to the correct department leadership asset (HR, Building & Housing, 311, Finance/Procurement, Public Health). Clarify intent with minimal questions, provide safe next steps, and escalate high-risk matters to human leadership.",
                is_router=True,
            ),
            AgentConfig(
                id="strategy",
                name="Dr. Elizabeth Crowe, PhD",
                title="Cleveland AI Strategy Advisor",
                domain="Strategy",
                description="Strategic advisor for the Cleveland AI opportunity. Provides deep insights, generates deal-making documents, and offers strategic guidance.",
                capabilities=["Strategic guidance", "Deal-making documents", "Pilot design", "Governance modeling"],
                guardrails=["No commitment impersonation", "Source-based responses only", "Flag missing information"],
                escalates_to="City Leadership",
                gpt_url="https://chatgpt.com/g/g-693f4d79d37881919210e12d92c8c92a-cleveland-ai-strategy-advisor",
                system_prompt="You are Dr. Elizabeth Crowe, PhD, the Cleveland AI Strategy Advisor. Provide strategic guidance for AI initiatives, generate deal-making documents, and offer insights based on your knowledge base. Never impersonate or make commitments on behalf of the City.",
            ),
            AgentConfig(
                id="public-health",
                name="Dr. David Margolius",
                title="Director of Public Health (CDPH)",
                domain="PublicHealth",
                description="Converts approved program guidance and public advisories into clear staff workflows and resident-facing drafts. Protects sensitive health information.",
                capabilities=["Staff workflow creation", "Resident-facing drafts", "Public advisory translation", "Health communication"],
                guardrails=["Protect PHI (HIPAA)", "No clinical advice", "Route PHI requests to privacy/legal", "No operational steps for sensitive data"],
                escalates_to="Public Health Leadership",
                gpt_url="https://chatgpt.com/g/g-693f576dc69c8191b7f84287c959f921-cleveland-public-health-leadership-asset",
                system_prompt="You are Dr. David Margolius, Director of Public Health for the City of Cleveland. Help staff with public health workflows and communications. NEVER provide clinical advice. ALWAYS protect PHI and route sensitive health data requests to privacy/legal teams.",
            ),
            AgentConfig(
                id="hr",
                name="Matthew J. Cole",
                title="HR Leadership Asset",
                domain="HR",
                description="Turns HR policies into clear guidance, drafts communications, supports managers, routes sensitive matters to HR leadership.",
                capabilities=["Policy interpretation", "Manager support", "Communication drafts", "Responsible AI guidance"],
                guardrails=["Privacy protection", "Fairness in guidance", "No employment decisions", "Route sensitive matters to HR leadership"],
                escalates_to="HR Leadership",
                gpt_url="https://chatgpt.com/g/g-693f5cebfc9c8191bb722a89b9b2e0c4-matthew-j-cole-cleveland-hr-leadership-asset",
                system_prompt="You are Matthew J. Cole, the Cleveland HR Leadership Asset. Help staff understand HR policies, draft communications, and support managers. Never make employment decisions. Route sensitive personnel matters to HR leadership for human review.",
            ),
            AgentConfig(
                id="finance",
                name="Ayesha Bell Hardaway",
                title="Chief Financial Officer",
                domain="Finance",
                description="Explains purchasing rules, budget processes, and vendor workflows from approved policies. Drafts compliant justifications and flags audit risks.",
                capabilities=["Purchasing rule guidance", "Budget process explanation", "Vendor workflow support", "Compliant draft generation"],
                guardrails=["No legal advice", "Flag audit risks", "Route exceptions to human", "Source from approved policies only"],
                escalates_to="Finance Leadership / Procurement",
                gpt_url="https://chatgpt.com/g/g-693f60021ab48191a767ca3c2c07b1b6-ayesha-bell-hardaway-finance-leadership-asset",
                system_prompt="You are Ayesha Bell Hardaway, Chief Financial Officer for the City of Cleveland. Help staff with purchasing rules, budget processes, and vendor workflows. Always flag audit risks and route exceptions for human approval. Never provide legal advice.",
            ),
            AgentConfig(
                id="building",
                name="Sally Martin O'Toole",
                title="Building & Housing Asset",
                domain="Building",
                description="Helps staff navigate permits, inspections, and customer guidance using approved procedures and code references.",
                capabilities=["Permit guidance", "Inspection procedures", "Code reference lookup", "Notice drafting"],
                guardrails=["Use approved procedures only", "Reference specific codes", "Route complex cases to experts", "No legal interpretations"],
                escalates_to="Building & Housing Leadership",
                gpt_url="https://chatgpt.com/g/g-693f6324e204819187b121395bd2903c-sally-martin-otoole-building-housing-asset",
                system_prompt="You are Sally Martin O'Toole, the Building & Housing Leadership Asset. Help staff and customers with permits, inspections, and building codes. Always reference specific code sections. Route complex interpretations to human experts.",
            ),
            AgentConfig(
                id="311",
                name="Kate Connor Warren",
                title="Director of Cleveland 311",
                domain="311",
                description="Improves first-contact resolution by guiding staff with scripts, service catalog rules, and escalation paths.",
                capabilities=["Script guidance", "Service catalog rules", "Escalation path routing", "Knowledge article refinement"],
                guardrails=["Follow service catalog", "Consistent response drafting", "Proper escalation paths", "No promises outside SLA"],
                escalates_to="311 Supervisors",
                gpt_url="https://chatgpt.com/g/g-693f66e109fc8191aee3b31b2458e2aa-cleveland-311-leadership-asset",
                system_prompt="You are Kate Connor Warren, Director of Cleveland 311. Help operators with scripts, service catalog rules, and escalation paths. Never promise services outside the standard SLA. Ensure consistent, fair treatment for all callers.",
            ),
            AgentConfig(
                id="gcp",
                name="Freddy Collier",
                title="SVP Strategy, Greater Cleveland Partnership",
                domain="Regional",
                description="Strategic AI leadership tool for regional alignment, governance narrative, and cross-sector coordination.",
                capabilities=["Regional alignment", "Cross-sector coordination", "Governance narrative", "Unified AI vision"],
                guardrails=["No City commitments", "Coordination focus only", "Route operational matters to City", "Narrative alignment, not execution"],
                escalates_to="GCP Leadership",
                gpt_url="https://chatgpt.com/g/g-6937851af410819181e24dedcc13d98c-leadership-asset-g-c-p-thinkin",
                system_prompt="You are Freddy Collier, SVP Strategy at Greater Cleveland Partnership. Focus on regional AI coordination and narrative alignment. Never make commitments on behalf of the City of Cleveland. Route operational matters to City departments.",
            ),
            AgentConfig(
                id="public-safety",
                name="Chief of Police",
                title="Public Safety Director",
                domain="PublicSafety",
                description="Crime analysis and DOJ Consent Decree compliance. Supports crime data analysis, CompStat reporting, policy guidance, and resource allocation.",
                capabilities=["Crime data analysis", "CompStat reporting", "DOJ Consent Decree compliance", "Policy and procedure guidance", "Resource allocation analysis"],
                guardrails=["Protect CJI (Criminal Justice Information)", "No operational dispatch commands", "Route officer-involved incidents to legal", "Use de-identified data only", "Mandatory escalation for emergencies"],
                escalates_to="Public Safety Leadership",
                gpt_url="",
                system_prompt="You are the Cleveland Public Safety Director Assistant. Help staff with crime data analysis, DOJ Consent Decree compliance tracking, policy guidance, and resource allocation. NEVER access or share Criminal Justice Information (CJI). ALWAYS use de-identified, aggregated data. Route officer-involved incidents and emergencies to appropriate leadership immediately.",
            ),
        ]
        for agent in defaults:
            self._agents[agent.id] = agent

    def list_agents(self) -> list[AgentConfig]:
        """List all agents."""
        return list(self._agents.values())

    def get_agent(self, agent_id: str) -> AgentConfig | None:
        """Get an agent by ID."""
        return self._agents.get(agent_id)

    def create_agent(self, agent: AgentConfig) -> AgentConfig:
        """Create a new agent."""
        agent.created_at = datetime.utcnow().isoformat()
        agent.updated_at = agent.created_at
        self._agents[agent.id] = agent
        self._save()
        return agent

    def update_agent(self, agent_id: str, updates: dict[str, Any]) -> AgentConfig | None:
        """Update an agent."""
        if agent_id not in self._agents:
            return None
        agent = self._agents[agent_id]
        for key, value in updates.items():
            if hasattr(agent, key) and key not in ("id", "created_at"):
                setattr(agent, key, value)
        agent.updated_at = datetime.utcnow().isoformat()
        self._agents[agent_id] = agent
        self._save()
        return agent

    def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent."""
        if agent_id in self._agents:
            del self._agents[agent_id]
            self._save()
            return True
        return False

    def enable_agent(self, agent_id: str) -> AgentConfig | None:
        """Enable an agent."""
        return self.update_agent(agent_id, {"status": "active"})

    def disable_agent(self, agent_id: str) -> AgentConfig | None:
        """Disable an agent."""
        return self.update_agent(agent_id, {"status": "inactive"})

    def get_router(self) -> AgentConfig | None:
        """Get the router agent (Concierge)."""
        for agent in self._agents.values():
            if agent.is_router:
                return agent
        return None


# Singleton instance
_agent_manager: AgentManager | None = None


def get_agent_manager() -> AgentManager:
    """Get the agent manager singleton."""
    global _agent_manager
    if _agent_manager is None:
        _agent_manager = AgentManager()
    return _agent_manager


__all__ = ["AgentConfig", "AgentManager", "get_agent_manager"]

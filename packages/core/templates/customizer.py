"""Template customization with LLM assistance.

Provides intelligent template customization by:
- Generating role-specific system prompts
- Adapting guardrails to context
- Suggesting capabilities based on requirements
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from packages.core.templates.types import (
    AgentTemplate,
    TemplateDomain,
    TemplateComplexity,
    HITLRequirement,
    MatchResult,
)


@dataclass
class CustomizationRequest:
    """Request for template customization."""

    # Template to customize
    template: AgentTemplate

    # Target configuration
    organization_name: str
    department_name: str
    role_name: str
    role_title: str

    # Context
    organization_context: dict[str, Any] = field(default_factory=dict)
    department_context: dict[str, Any] = field(default_factory=dict)

    # Customization preferences
    additional_capabilities: list[str] = field(default_factory=list)
    additional_guardrails: list[str] = field(default_factory=list)
    hitl_override: HITLRequirement | None = None
    escalation_path: str | None = None

    # Data sources
    knowledge_sources: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class CustomizedAgent:
    """Result of template customization."""

    # Identity
    agent_id: str
    name: str
    title: str
    description: str

    # Configuration
    domain: str
    system_prompt: str
    capabilities: list[str]
    guardrails: list[str]
    hitl_mode: str
    escalation_path: str

    # Source
    base_template_id: str
    customizations_applied: list[str]

    # Metadata
    organization_id: str
    department_id: str
    is_active: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "domain": self.domain,
            "system_prompt": self.system_prompt,
            "capabilities": self.capabilities,
            "guardrails": self.guardrails,
            "hitl_mode": self.hitl_mode,
            "escalation_path": self.escalation_path,
            "base_template_id": self.base_template_id,
            "customizations_applied": self.customizations_applied,
            "organization_id": self.organization_id,
            "department_id": self.department_id,
            "is_active": self.is_active,
        }


class TemplateCustomizer:
    """Customizes templates for specific organizational contexts.

    Can operate in two modes:
    1. Rule-based customization (fast, no LLM)
    2. LLM-assisted customization (intelligent, requires LLM)
    """

    def __init__(self, llm_router: Any | None = None):
        """Initialize customizer.

        Args:
            llm_router: Optional LLM router for intelligent customization
        """
        self._llm_router = llm_router

    def customize(
        self,
        request: CustomizationRequest,
        use_llm: bool = False,
    ) -> CustomizedAgent:
        """Customize a template for a specific context.

        Args:
            request: Customization request
            use_llm: Whether to use LLM for intelligent customization

        Returns:
            Customized agent configuration
        """
        if use_llm and self._llm_router:
            return self._customize_with_llm(request)
        return self._customize_rule_based(request)

    def _customize_rule_based(
        self,
        request: CustomizationRequest,
    ) -> CustomizedAgent:
        """Apply rule-based customization."""
        template = request.template
        customizations = []

        # Generate system prompt
        system_prompt = self._generate_system_prompt(request)
        customizations.append("system_prompt_generated")

        # Combine capabilities
        capabilities = list(template.capability_names)
        if request.additional_capabilities:
            capabilities.extend(request.additional_capabilities)
            customizations.append("capabilities_extended")

        # Combine guardrails
        guardrails = list(template.guardrail_rules)
        if request.additional_guardrails:
            guardrails.extend(request.additional_guardrails)
            customizations.append("guardrails_extended")

        # Determine HITL mode
        hitl_mode = request.hitl_override or template.default_hitl_mode
        if request.hitl_override:
            customizations.append("hitl_mode_overridden")

        # Set escalation path
        escalation = request.escalation_path or template.default_escalation_path
        if request.escalation_path:
            customizations.append("escalation_path_set")

        # Generate agent ID
        agent_id = self._generate_agent_id(
            request.organization_name,
            request.department_name,
        )

        # Build description
        description = self._generate_description(request, template)

        return CustomizedAgent(
            agent_id=agent_id,
            name=request.role_name,
            title=request.role_title,
            description=description,
            domain=template.domain.value if isinstance(template.domain, TemplateDomain) else template.domain,
            system_prompt=system_prompt,
            capabilities=capabilities,
            guardrails=guardrails,
            hitl_mode=hitl_mode.value if isinstance(hitl_mode, HITLRequirement) else hitl_mode,
            escalation_path=escalation,
            base_template_id=template.template_id,
            customizations_applied=customizations,
            organization_id=self._slugify(request.organization_name),
            department_id=self._slugify(request.department_name),
        )

    def _generate_system_prompt(self, request: CustomizationRequest) -> str:
        """Generate system prompt from template and context."""
        template = request.template

        # Start with template's system prompt
        prompt = template.system_prompt_template

        # Substitute basic placeholders
        substitutions = {
            "{org_name}": request.organization_name,
            "{department_name}": request.department_name,
            "{role_name}": request.role_name,
            "{role_title}": request.role_title,
        }

        for placeholder, value in substitutions.items():
            prompt = prompt.replace(placeholder, value)

        # Add context sections if available
        if request.organization_context:
            for key, value in request.organization_context.items():
                placeholder = "{" + key + "}"
                if placeholder in prompt:
                    if isinstance(value, list):
                        value = "\n".join(f"- {v}" for v in value)
                    prompt = prompt.replace(placeholder, str(value))

        if request.department_context:
            for key, value in request.department_context.items():
                placeholder = "{" + key + "}"
                if placeholder in prompt:
                    if isinstance(value, list):
                        value = "\n".join(f"- {v}" for v in value)
                    prompt = prompt.replace(placeholder, str(value))

        # Clean up any remaining placeholders
        import re
        prompt = re.sub(r'\{[^}]+\}', '[To be configured]', prompt)

        # Add HAAIS governance footer
        prompt += f"""

---
HAAIS GOVERNANCE:
- Human-in-the-Loop Mode: {request.hitl_override or template.default_hitl_mode}
- Escalation Path: {request.escalation_path or template.default_escalation_path}
- Classification: {template.complexity.value if isinstance(template.complexity, TemplateComplexity) else template.complexity}
"""

        return prompt

    def _generate_description(
        self,
        request: CustomizationRequest,
        template: AgentTemplate,
    ) -> str:
        """Generate agent description."""
        base_desc = template.description

        # Customize for organization
        desc = f"AI assistant for {request.organization_name} {request.department_name}. "
        desc += base_desc

        return desc

    def _generate_agent_id(self, org_name: str, dept_name: str) -> str:
        """Generate unique agent ID."""
        return f"{self._slugify(org_name)}-{self._slugify(dept_name)}"

    def _slugify(self, text: str) -> str:
        """Convert text to slug format."""
        import re
        text = text.lower()
        text = re.sub(r'[^a-z0-9]+', '-', text)
        text = text.strip('-')
        return text[:50]  # Limit length

    async def _customize_with_llm(
        self,
        request: CustomizationRequest,
    ) -> CustomizedAgent:
        """Use LLM for intelligent customization."""
        # First, do rule-based customization as base
        base_agent = self._customize_rule_based(request)

        if not self._llm_router:
            return base_agent

        # Use LLM to enhance system prompt
        enhanced_prompt = await self._enhance_system_prompt_with_llm(
            request, base_agent.system_prompt
        )

        # Use LLM to suggest additional guardrails
        enhanced_guardrails = await self._enhance_guardrails_with_llm(
            request, base_agent.guardrails
        )

        base_agent.system_prompt = enhanced_prompt
        base_agent.guardrails = enhanced_guardrails
        base_agent.customizations_applied.append("llm_enhanced")

        return base_agent

    async def _enhance_system_prompt_with_llm(
        self,
        request: CustomizationRequest,
        base_prompt: str,
    ) -> str:
        """Enhance system prompt using LLM."""
        from packages.core.llm.types import Task, TaskType

        task = Task(
            task_id="prompt-enhancement",
            task_type=TaskType.CONTENT_GENERATION,
            prompt=f"""Enhance this system prompt for a municipal AI assistant.

BASE PROMPT:
{base_prompt}

CONTEXT:
- Organization: {request.organization_name}
- Department: {request.department_name}
- Role: {request.role_title}

Enhance the prompt to be more specific and helpful while maintaining all governance requirements.
Keep the HAAIS governance footer intact.
Return only the enhanced prompt, no explanation.""",
            organization_id=self._slugify(request.organization_name),
            requires_generation=True,
            max_tokens=4000,
        )

        try:
            result = await self._llm_router.execute(
                task=task,
                prompt=task.prompt,
            )
            if result.success and result.response:
                return result.response.content
        except Exception:
            pass

        return base_prompt

    async def _enhance_guardrails_with_llm(
        self,
        request: CustomizationRequest,
        base_guardrails: list[str],
    ) -> list[str]:
        """Suggest additional guardrails using LLM."""
        from packages.core.llm.types import Task, TaskType

        task = Task(
            task_id="guardrail-enhancement",
            task_type=TaskType.GOVERNANCE_EVALUATION,
            prompt=f"""Review these guardrails for a municipal AI assistant and suggest 2-3 additional domain-specific guardrails.

CURRENT GUARDRAILS:
{json.dumps(base_guardrails, indent=2)}

CONTEXT:
- Organization: {request.organization_name}
- Department: {request.department_name}
- Role: {request.role_title}
- Domain: {request.template.domain.value if isinstance(request.template.domain, TemplateDomain) else request.template.domain}

Return a JSON array of 2-3 new guardrails that should be added (not duplicates of existing ones).
Each guardrail should start with "NEVER" and be specific to this domain.
Return only the JSON array, no explanation.""",
            organization_id=self._slugify(request.organization_name),
            requires_json=True,
            max_tokens=1000,
        )

        try:
            result = await self._llm_router.execute(
                task=task,
                prompt=task.prompt,
            )
            if result.success and result.response:
                additional = json.loads(result.response.content)
                if isinstance(additional, list):
                    return base_guardrails + additional
        except Exception:
            pass

        return base_guardrails


class BatchCustomizer:
    """Handles batch customization of templates for multiple departments."""

    def __init__(self, customizer: TemplateCustomizer | None = None):
        self._customizer = customizer or TemplateCustomizer()

    def customize_organization(
        self,
        org_name: str,
        department_configs: list[dict[str, Any]],
        match_results: dict[str, list[MatchResult]],
    ) -> list[CustomizedAgent]:
        """Customize templates for an entire organization.

        Args:
            org_name: Organization name
            department_configs: List of department configurations
            match_results: Template matches for each department

        Returns:
            List of customized agents
        """
        agents = []

        for dept_config in department_configs:
            dept_name = dept_config.get("name", "Unknown")
            matches = match_results.get(dept_name, [])

            if not matches:
                continue

            # Use best match
            best_match = matches[0]

            request = CustomizationRequest(
                template=best_match.template,
                organization_name=org_name,
                department_name=dept_name,
                role_name=dept_config.get("director_name", "Director"),
                role_title=dept_config.get("director_title", f"Director of {dept_name}"),
                organization_context=dept_config.get("org_context", {}),
                department_context=dept_config.get("context", {}),
                additional_capabilities=dept_config.get("additional_capabilities", []),
                additional_guardrails=dept_config.get("additional_guardrails", []),
            )

            agent = self._customizer.customize(request)
            agents.append(agent)

        return agents

    def generate_manifest(
        self,
        org_name: str,
        agents: list[CustomizedAgent],
    ) -> dict[str, Any]:
        """Generate deployment manifest for agents.

        Args:
            org_name: Organization name
            agents: List of customized agents

        Returns:
            Deployment manifest
        """
        return {
            "manifest_version": "1.0",
            "organization": org_name,
            "generated_at": self._get_timestamp(),
            "agents": [agent.to_dict() for agent in agents],
            "router_config": self._generate_router_config(agents),
            "deployment_notes": self._generate_deployment_notes(agents),
        }

    def _generate_router_config(
        self,
        agents: list[CustomizedAgent],
    ) -> dict[str, Any]:
        """Generate router configuration for agents."""
        routing_rules = []

        for agent in agents:
            if agent.domain == "router":
                continue

            routing_rules.append({
                "agent_id": agent.agent_id,
                "domain": agent.domain,
                "keywords": self._extract_keywords(agent),
                "capabilities": agent.capabilities,
            })

        return {
            "rules": routing_rules,
            "fallback_agent": "concierge",
            "clarification_threshold": 0.7,
        }

    def _extract_keywords(self, agent: CustomizedAgent) -> list[str]:
        """Extract routing keywords from agent."""
        keywords = []

        # Add domain as keyword
        keywords.append(agent.domain)

        # Extract from title
        keywords.extend(agent.title.lower().split())

        # Extract from capabilities
        for cap in agent.capabilities[:5]:
            keywords.extend(cap.lower().split()[:3])

        # Dedupe and clean
        return list(set(
            kw for kw in keywords
            if len(kw) > 2 and kw not in ["the", "and", "for", "with"]
        ))

    def _generate_deployment_notes(
        self,
        agents: list[CustomizedAgent],
    ) -> list[str]:
        """Generate deployment notes."""
        notes = []

        # Check for router
        has_router = any(a.domain == "router" for a in agents)
        if not has_router:
            notes.append("IMPORTANT: No router agent configured. Consider adding a router-concierge agent.")

        # Check HITL modes
        escalate_agents = [a for a in agents if a.hitl_mode == "escalate"]
        if escalate_agents:
            notes.append(
                f"REVIEW: {len(escalate_agents)} agent(s) require human escalation for all actions. "
                f"Ensure escalation paths are staffed."
            )

        # Check high-complexity agents
        enterprise_count = sum(
            1 for a in agents
            if "enterprise" in a.customizations_applied or "regulatory" in a.domain.lower()
        )
        if enterprise_count:
            notes.append(
                f"COMPLIANCE: {enterprise_count} enterprise-grade agent(s) may require additional compliance review."
            )

        return notes

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.utcnow().isoformat()

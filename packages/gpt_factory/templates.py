"""
Template Engine

Generates agent configurations from archetypes and discovered data.
Uses Jinja2-style templating with custom filters for agent-specific needs.
"""

from __future__ import annotations
import re
from string import Template
from typing import Optional, Any

from .models import (
    Organization,
    AgentCandidate,
    AgentBlueprint,
    Capability,
    Guardrail,
    KnowledgeSource,
    GovernanceConfig,
)
from .archetypes import Archetype, ArchetypeRegistry


class TemplateEngine:
    """
    Generates agent blueprints from archetypes and organizational data.

    The template engine:
    1. Takes an archetype (template) and candidate (discovered data)
    2. Merges them with organization context
    3. Produces a complete AgentBlueprint ready for deployment
    """

    def __init__(self, registry: Optional[ArchetypeRegistry] = None):
        self.registry = registry or ArchetypeRegistry()

    def generate_blueprint(
        self,
        candidate: AgentCandidate,
        organization: Organization,
        archetype: Optional[Archetype] = None,
        overrides: Optional[dict[str, Any]] = None,
    ) -> AgentBlueprint:
        """
        Generate a complete agent blueprint from candidate and archetype.

        Args:
            candidate: The discovered agent candidate
            organization: The organization context
            archetype: Optional archetype to use (auto-detected if not provided)
            overrides: Optional field overrides

        Returns:
            Complete AgentBlueprint ready for validation/deployment
        """
        # Auto-detect archetype if not provided
        if archetype is None:
            archetype = self.registry.best_match(
                organization.type,
                candidate.type,
            )

        # Build template context
        context = self._build_context(candidate, organization, archetype)

        # Generate blueprint
        blueprint = AgentBlueprint(
            id=self._generate_id(candidate),
            organization_id=organization.id,
            archetype_id=archetype.id if archetype else None,
            name=self._render(candidate.suggested_agent_name, context),
            title=self._render(
                archetype.title_template if archetype else candidate.name,
                context
            ),
            domain=archetype.domain if archetype else "General",
            description_short=self._generate_short_description(
                candidate, organization, archetype, context
            ),
            description_full=self._generate_full_description(
                candidate, organization, archetype, context
            ),
            instructions=self._generate_instructions(
                candidate, organization, archetype, context
            ),
            capabilities=self._merge_capabilities(candidate, archetype),
            guardrails=self._merge_guardrails(candidate, archetype),
            governance=self._build_governance(archetype),
            conversation_starters=self._generate_conversation_starters(
                archetype, context
            ),
            escalates_to=archetype.typical_escalation if archetype else None,
            collaborates_with=archetype.typical_collaborators if archetype else [],
            is_router=archetype.metadata.get("is_router", False) if archetype else False,
        )

        # Apply overrides
        if overrides:
            for key, value in overrides.items():
                if hasattr(blueprint, key):
                    setattr(blueprint, key, value)

        return blueprint

    def _build_context(
        self,
        candidate: AgentCandidate,
        organization: Organization,
        archetype: Optional[Archetype],
    ) -> dict[str, Any]:
        """Build the template rendering context."""
        return {
            # Organization
            "organization": organization.name,
            "organization_type": organization.type.value,
            "organization_url": organization.url,

            # Candidate
            "candidate_name": candidate.name,
            "candidate_type": candidate.type.value,
            "department": candidate.name,

            # Agent
            "agent_name": candidate.suggested_agent_name,
            "agent_title": archetype.title_template if archetype else candidate.name,

            # Contact (if available)
            "contact_name": candidate.contact.name if candidate.contact else None,
            "contact_email": candidate.contact.email if candidate.contact else None,
            "contact_phone": candidate.contact.phone if candidate.contact else None,

            # Archetype metadata
            "domain": archetype.domain if archetype else "General",

            # Placeholders for runtime injection
            "agent_roster": "{agent_roster}",  # Filled at deployment
            "purchasing_thresholds": "{purchasing_thresholds}",
            "permit_types": "{permit_types}",
            "service_categories": "{service_categories}",
        }

    def _render(self, template_str: str, context: dict[str, Any]) -> str:
        """Render a template string with the given context."""
        if not template_str:
            return ""

        try:
            # Use safe substitution to handle missing keys gracefully
            template = Template(template_str)
            return template.safe_substitute(context)
        except Exception:
            return template_str

    def _generate_id(self, candidate: AgentCandidate) -> str:
        """Generate a unique ID for the agent."""
        # Convert name to slug
        slug = candidate.name.lower()
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        slug = slug.strip('-')
        return slug

    def _generate_short_description(
        self,
        candidate: AgentCandidate,
        organization: Organization,
        archetype: Optional[Archetype],
        context: dict[str, Any],
    ) -> str:
        """Generate a short description (fits OpenAI 300 char limit)."""
        if archetype and archetype.description_template:
            desc = self._render(archetype.description_template, context)
        elif candidate.description:
            desc = candidate.description
        else:
            desc = f"Expert assistant for {candidate.name} at {organization.name}"

        # Truncate to 300 chars if needed (OpenAI limit)
        if len(desc) > 300:
            desc = desc[:297] + "..."

        return desc

    def _generate_full_description(
        self,
        candidate: AgentCandidate,
        organization: Organization,
        archetype: Optional[Archetype],
        context: dict[str, Any],
    ) -> str:
        """Generate a full description (no limit for AIOS)."""
        parts = []

        # Main description
        if archetype and archetype.description_template:
            parts.append(self._render(archetype.description_template, context))
        elif candidate.description:
            parts.append(candidate.description)

        # Add capabilities summary
        if archetype and archetype.default_capabilities:
            parts.append("\n\n## Capabilities")
            for cap in archetype.default_capabilities:
                parts.append(f"- **{cap.name}**: {cap.description}")

        # Add contact info if available
        if candidate.contact:
            parts.append("\n\n## Contact")
            if candidate.contact.email:
                parts.append(f"- Email: {candidate.contact.email}")
            if candidate.contact.phone:
                parts.append(f"- Phone: {candidate.contact.phone}")

        return "\n".join(parts)

    def _generate_instructions(
        self,
        candidate: AgentCandidate,
        organization: Organization,
        archetype: Optional[Archetype],
        context: dict[str, Any],
    ) -> str:
        """Generate full system instructions (no limit for AIOS)."""
        if archetype and archetype.instruction_template:
            instructions = self._render(archetype.instruction_template, context)
        else:
            # Generate basic instructions
            instructions = self._generate_basic_instructions(
                candidate, organization, context
            )

        # Append HAAIS governance framework
        instructions += "\n\n" + self._get_governance_appendix()

        return instructions

    def _generate_basic_instructions(
        self,
        candidate: AgentCandidate,
        organization: Organization,
        context: dict[str, Any],
    ) -> str:
        """Generate basic instructions when no archetype is available."""
        return f"""You are an AI assistant for {candidate.name} at {organization.name}.

## Your Role
You help employees with questions and tasks related to {candidate.name}. You are knowledgeable about department policies, procedures, and services.

## Guidelines
- Answer questions accurately based on your knowledge base
- Cite sources when providing policy information
- Acknowledge when you're unsure and recommend appropriate contacts
- Maintain professional, helpful tone

## Boundaries
- Do not make decisions that require human authority
- Do not disclose confidential information
- Escalate sensitive matters to appropriate personnel

## Escalation
For matters beyond your scope, direct users to the appropriate department or supervisor.
"""

    def _get_governance_appendix(self) -> str:
        """Get the HAAIS governance framework appendix."""
        return """---

## HAAIS Governance Framework

This agent operates under the HAAIS AI governance framework, which ensures:

### Source Attribution
All responses are grounded in authoritative sources. When providing policy information:
- Cite the specific document and section
- Indicate the authority level (policy, ordinance, procedure)
- Note if human verification is recommended

### Human-in-the-Loop Modes
Depending on the query's sensitivity, responses may be:
- **INFORM**: Delivered immediately (low-risk queries)
- **DRAFT**: Held for human review before delivery
- **EXECUTE**: Require manager approval
- **ESCALATE**: Transferred to human specialist

### Audit Trail
All interactions are logged for accountability and continuous improvement.

### Guardrails
Hard constraints prevent the agent from:
- Making decisions requiring human authority
- Disclosing protected information
- Providing advice outside its expertise

For questions about this framework, contact the AI Governance team.
"""

    def _merge_capabilities(
        self,
        candidate: AgentCandidate,
        archetype: Optional[Archetype],
    ) -> list[Capability]:
        """Merge capabilities from archetype with candidate-specific ones."""
        capabilities = []

        # Add archetype defaults
        if archetype:
            capabilities.extend(archetype.default_capabilities)

        # Add any candidate-specific capabilities from metadata
        if "capabilities" in candidate.metadata:
            for cap_data in candidate.metadata["capabilities"]:
                capabilities.append(Capability(**cap_data))

        return capabilities

    def _merge_guardrails(
        self,
        candidate: AgentCandidate,
        archetype: Optional[Archetype],
    ) -> list[Guardrail]:
        """Merge guardrails from archetype with candidate-specific ones."""
        guardrails = []

        # Add archetype defaults
        if archetype:
            guardrails.extend(archetype.default_guardrails)

        # Add any candidate-specific guardrails from metadata
        if "guardrails" in candidate.metadata:
            for guard_data in candidate.metadata["guardrails"]:
                guardrails.append(Guardrail(**guard_data))

        return guardrails

    def _build_governance(
        self,
        archetype: Optional[Archetype],
    ) -> GovernanceConfig:
        """Build governance configuration from archetype."""
        if archetype:
            return archetype.default_governance
        return GovernanceConfig()

    def _generate_conversation_starters(
        self,
        archetype: Optional[Archetype],
        context: dict[str, Any],
    ) -> list[str]:
        """Generate conversation starters."""
        if archetype and archetype.default_conversation_starters:
            return [
                self._render(starter, context)
                for starter in archetype.default_conversation_starters
            ]
        return [
            "How can I help you today?",
            "What questions do you have?",
            "I'm here to assist with department matters.",
        ]

    def generate_instructions_summary(
        self,
        blueprint: AgentBlueprint,
        max_length: int = 8000,
    ) -> str:
        """
        Generate a condensed version of instructions for platforms with limits.

        Used when exporting to OpenAI Custom GPTs (8000 char limit).
        """
        instructions = blueprint.instructions

        if len(instructions) <= max_length:
            return instructions

        # Strategy: Keep core sections, summarize others
        sections = instructions.split("\n## ")
        priority_sections = ["Your Role", "How You Help", "Boundaries", "Escalation"]

        kept = []
        remaining_budget = max_length - 500  # Reserve space for header/footer

        # Always keep the header (before first ##)
        if sections[0]:
            header = sections[0][:500]
            kept.append(header)
            remaining_budget -= len(header)

        # Prioritize important sections
        for section_name in priority_sections:
            for section in sections[1:]:
                if section.startswith(section_name):
                    section_text = "## " + section
                    if len(section_text) <= remaining_budget:
                        kept.append(section_text)
                        remaining_budget -= len(section_text)
                    break

        # Add truncation notice
        kept.append("\n\n---\n*Note: Full instructions available in AIOS deployment.*")

        return "\n".join(kept)

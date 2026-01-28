"""ChatGPT Custom GPT adapter."""

from __future__ import annotations

from typing import Any

from packages.onboarding.platforms.base import (
    PlatformAdapter,
    PlatformConfig,
    PlatformType,
    AgentOutput,
)
from packages.onboarding.platforms.constraints import (
    PLATFORM_CONSTRAINTS,
    get_starters_for_department,
)


class ChatGPTAdapter(PlatformAdapter):
    """Adapter for ChatGPT Custom GPTs."""

    platform = PlatformType.CHATGPT

    def get_constraints(self) -> dict[str, Any]:
        """Get ChatGPT constraints."""
        return PLATFORM_CONSTRAINTS["chatgpt"]

    def adapt(
        self,
        manifest: Any,
        platform_config: PlatformConfig,
    ) -> AgentOutput:
        """Convert agent manifest to ChatGPT Custom GPT format."""
        constraints = self.get_constraints()
        warnings = []

        # Build name (max 50 chars)
        name = self.truncate(manifest.name, constraints["name"]["max_chars"])
        if len(manifest.name) > constraints["name"]["max_chars"]:
            warnings.append(f"Name truncated from {len(manifest.name)} to {constraints['name']['max_chars']} chars")

        # Build description (max 300 chars)
        description = self._build_description(manifest, constraints["description"]["max_chars"])
        if len(manifest.description) > constraints["description"]["max_chars"]:
            warnings.append("Description truncated to fit 300 char limit")

        # Build instructions (max 8000 chars)
        instructions = self._build_instructions(manifest, constraints["instructions"]["max_chars"])
        if len(manifest.system_prompt) > constraints["instructions"]["max_chars"]:
            warnings.append("Instructions compressed to fit 8000 char limit")

        # Prepare knowledge files (max 20)
        knowledge_files = self._prepare_knowledge_files(manifest, constraints)
        if len(manifest.data_source_ids) > constraints["knowledge_files"]["max_count"]:
            warnings.append(f"Knowledge files limited to {constraints['knowledge_files']['max_count']} (had {len(manifest.data_source_ids)})")

        # Get conversation starters (max 4)
        starters = get_starters_for_department(
            manifest.id,
            "chatgpt",
            manifest.name,
        )

        # Build the GPT configuration
        config = {
            "name": name,
            "description": description,
            "instructions": instructions,
            "conversation_starters": starters,
            "capabilities": {
                "web_browsing": platform_config.chatgpt_enable_web_browsing,
                "code_interpreter": platform_config.chatgpt_enable_code_interpreter,
                "dall_e": platform_config.chatgpt_enable_dalle,
            },
            "visibility": platform_config.chatgpt_visibility,
        }

        # Manual steps for GPT creation
        manual_steps = [
            "1. Go to https://chat.openai.com/gpts/editor",
            "2. Click 'Create a GPT'",
            "3. In the 'Configure' tab:",
            f"   - Name: {name}",
            f"   - Description: (see config)",
            "   - Instructions: (paste from config)",
            "4. Add conversation starters",
            "5. Upload knowledge files",
            "6. Set capabilities as configured",
            f"7. Set visibility to '{platform_config.chatgpt_visibility}'",
            "8. Click 'Save' to create the GPT",
        ]

        return AgentOutput(
            platform=self.platform,
            agent_id=manifest.id,
            agent_name=name,
            config=config,
            files=knowledge_files,
            manual_steps=manual_steps,
            warnings=warnings,
        )

    def _build_description(self, manifest: Any, max_chars: int) -> str:
        """Build a concise description for the GPT."""
        # Start with the title and core purpose
        desc = f"{manifest.title} for municipal government. "

        # Add key capabilities
        if manifest.capabilities:
            caps = ", ".join(manifest.capabilities[:3])
            desc += f"Capabilities: {caps}. "

        # Add governance note
        desc += "HAAIS-governed for responsible AI use."

        return self.truncate(desc, max_chars)

    def _build_instructions(self, manifest: Any, max_chars: int) -> str:
        """Build instructions optimized for ChatGPT's 8000 char limit."""
        sections = []

        # Section 1: Identity (always include)
        identity = f"""## IDENTITY
You are {manifest.name}, {manifest.title}.
Domain: {manifest.domain}
{manifest.description}"""
        sections.append(identity)

        # Section 2: Capabilities
        if manifest.capabilities:
            caps = "\n".join(f"- {c}" for c in manifest.capabilities)
            sections.append(f"## CAPABILITIES\n{caps}")

        # Section 3: Guardrails (critical - always include)
        if manifest.guardrails:
            rails = "\n".join(f"- {g}" for g in manifest.guardrails)
            sections.append(f"## GUARDRAILS (MUST FOLLOW)\n{rails}")

        # Section 4: Escalation
        sections.append(f"""## ESCALATION
When uncertain or when requests involve:
- Legal matters
- Personnel decisions
- Policy exceptions
- Safety concerns
Escalate to: {manifest.escalates_to}""")

        # Section 5: HAAIS Governance (abbreviated for space)
        sections.append("""## GOVERNANCE FRAMEWORK
This agent operates under HAAIS (Human Assisted AI Services) governance:
- INFORM: Provide information, no action
- DRAFT: Create drafts for human review
- EXECUTE: Take action with audit trail
- ESCALATE: Route to human decision-maker

Always identify yourself as an AI assistant. Never impersonate city officials.""")

        # Combine and compress if needed
        full_instructions = "\n\n".join(sections)

        if len(full_instructions) <= max_chars:
            return full_instructions

        return self.compress_instructions(full_instructions, max_chars)

    def _prepare_knowledge_files(
        self, manifest: Any, constraints: dict
    ) -> list[dict[str, Any]]:
        """Prepare knowledge files for upload."""
        files = []
        max_files = constraints["knowledge_files"]["max_count"]

        # Add governance document
        files.append({
            "name": "HAAIS_Governance_Framework.md",
            "type": "governance",
            "content_template": "haais_governance",
            "priority": 1,
        })

        # Add department-specific files
        for i, source_id in enumerate(manifest.data_source_ids[:max_files - 1]):
            files.append({
                "name": f"data_source_{source_id}.json",
                "type": "data_reference",
                "source_id": source_id,
                "priority": i + 2,
            })

        return files[:max_files]

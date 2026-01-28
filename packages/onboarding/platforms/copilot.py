"""Microsoft Copilot Studio adapter.

Primary target for Microsoft 365 environments like Cleveland.
"""

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


class CopilotStudioAdapter(PlatformAdapter):
    """Adapter for Microsoft Copilot Studio."""

    platform = PlatformType.COPILOT_STUDIO

    def get_constraints(self) -> dict[str, Any]:
        """Get Copilot Studio constraints."""
        return PLATFORM_CONSTRAINTS["copilot_studio"]

    def adapt(
        self,
        manifest: Any,
        platform_config: PlatformConfig,
    ) -> AgentOutput:
        """Convert agent manifest to Copilot Studio format."""
        constraints = self.get_constraints()
        warnings = []

        # Build name (max 100 chars)
        name = self.truncate(manifest.name, constraints["name"]["max_chars"])

        # Build description (max 1000 chars)
        description = self._build_description(manifest, constraints["description"]["max_chars"])

        # Build system message (max 6000 chars)
        # Note: Some logic moves to Topics in Copilot
        system_message = self._build_system_message(manifest, constraints["instructions"]["max_chars"])
        if len(manifest.system_prompt) > constraints["instructions"]["max_chars"]:
            warnings.append("System message compressed; HITL modes moved to Topics")

        # Generate Topics for conversation flows
        topics = self._generate_topics(manifest)

        # Get suggested actions (max 6)
        suggested_actions = get_starters_for_department(
            manifest.id,
            "copilot_studio",
            manifest.name,
        )

        # Prepare knowledge sources (SharePoint integration)
        knowledge_sources = self._prepare_knowledge_sources(manifest, platform_config)

        # Build the Copilot configuration
        config = {
            "name": name,
            "description": description,
            "system_message": system_message,
            "topics": topics,
            "suggested_actions": suggested_actions,
            "knowledge_sources": knowledge_sources,
            "settings": {
                "generative_answers": True,
                "authentication": "azure_ad",
                "channels": ["teams", "web"],
            },
            "governance": {
                "dlp_policy": platform_config.copilot_dlp_policy,
                "audit_enabled": True,
            },
        }

        # Copilot Studio deployment configuration
        deployment_config = {
            "solution": platform_config.copilot_solution or f"{manifest.id}_solution",
            "environment": platform_config.environment,
            "sharepoint_site": platform_config.copilot_sharepoint_site,
            "teams_channel": platform_config.copilot_teams_channel,
        }

        # Manual steps and API calls
        manual_steps = self._generate_manual_steps(manifest, platform_config)
        api_calls = self._generate_api_calls(config, deployment_config)

        return AgentOutput(
            platform=self.platform,
            agent_id=manifest.id,
            agent_name=name,
            config={**config, "deployment": deployment_config},
            files=self._generate_export_files(config),
            manual_steps=manual_steps,
            warnings=warnings,
            api_calls=api_calls,
        )

    def _build_description(self, manifest: Any, max_chars: int) -> str:
        """Build description for Copilot."""
        desc = f"{manifest.title} - {manifest.domain} Department Leadership Asset. "
        desc += manifest.description[:500] if manifest.description else ""
        desc += f" Escalates to: {manifest.escalates_to}."
        return self.truncate(desc, max_chars)

    def _build_system_message(self, manifest: Any, max_chars: int) -> str:
        """Build system message optimized for Copilot's 6000 char limit.

        Note: MODE_ASSIGNMENTS move to Topics for better UX in Copilot.
        """
        sections = []

        # Identity
        sections.append(f"""You are {manifest.name}, {manifest.title}.
You serve as the AI Leadership Asset for the {manifest.domain} domain.

{manifest.description}""")

        # Capabilities
        if manifest.capabilities:
            caps = "\n".join(f"• {c}" for c in manifest.capabilities)
            sections.append(f"""WHAT I CAN HELP WITH:
{caps}""")

        # Guardrails (critical)
        if manifest.guardrails:
            rails = "\n".join(f"• {g}" for g in manifest.guardrails)
            sections.append(f"""IMPORTANT BOUNDARIES:
{rails}""")

        # Escalation
        sections.append(f"""ESCALATION:
If you encounter requests involving legal matters, personnel decisions, policy exceptions, or safety concerns, acknowledge the request and direct the user to contact {manifest.escalates_to}.

Always identify yourself as an AI assistant powered by HAAIS governance.""")

        full_message = "\n\n".join(sections)

        if len(full_message) <= max_chars:
            return full_message

        return self.compress_instructions(full_message, max_chars)

    def _generate_topics(self, manifest: Any) -> list[dict[str, Any]]:
        """Generate Copilot Topics for conversation flows.

        Topics replace some instruction logic for better Copilot UX.
        """
        topics = []

        # Greeting topic
        topics.append({
            "name": "Greeting",
            "trigger_phrases": [
                "hello", "hi", "hey", "good morning", "good afternoon",
                "help", "what can you do", "get started"
            ],
            "response": f"Hello! I'm {manifest.name}, your {manifest.title}. I can help you with {', '.join(manifest.capabilities[:3]) if manifest.capabilities else 'department inquiries'}. What would you like assistance with today?",
            "type": "system",
        })

        # INFORM mode topic
        topics.append({
            "name": "Information Request",
            "trigger_phrases": [
                "what is", "tell me about", "explain", "how does",
                "information on", "details about", "describe"
            ],
            "response": "I'll provide information on that topic. [Generative Answer]",
            "type": "inform",
            "hitl_mode": "INFORM",
        })

        # DRAFT mode topic
        topics.append({
            "name": "Draft Creation",
            "trigger_phrases": [
                "draft", "write", "create", "compose", "prepare",
                "help me write", "generate"
            ],
            "response": "I'll create a draft for your review. Please note this is a DRAFT that requires human review before use. [Generative Answer]\n\n⚠️ This draft requires review by appropriate staff before distribution.",
            "type": "draft",
            "hitl_mode": "DRAFT",
        })

        # Escalation topic
        topics.append({
            "name": "Escalation Required",
            "trigger_phrases": [
                "legal", "lawsuit", "attorney", "confidential",
                "personnel action", "termination", "discipline",
                "emergency", "urgent", "media", "press"
            ],
            "response": f"This request involves matters that require human oversight. Please contact {manifest.escalates_to} directly for assistance with this matter.\n\nI can help you prepare any background information or draft initial documents for their review.",
            "type": "escalate",
            "hitl_mode": "ESCALATE",
        })

        # Fallback topic
        topics.append({
            "name": "Fallback",
            "trigger_phrases": [],  # Catches unmatched
            "response": f"I'm not sure I understood that request. I'm {manifest.name}, and I specialize in {manifest.domain} matters. Could you rephrase your question, or would you like to know what I can help with?",
            "type": "fallback",
        })

        return topics

    def _prepare_knowledge_sources(
        self, manifest: Any, platform_config: PlatformConfig
    ) -> list[dict[str, Any]]:
        """Prepare SharePoint-based knowledge sources."""
        sources = []

        base_site = platform_config.copilot_sharepoint_site or "https://tenant.sharepoint.com/sites/AI_Knowledge"

        # Governance library
        sources.append({
            "type": "sharepoint_site",
            "url": f"{base_site}/Governance",
            "name": "HAAIS Governance Documents",
            "include_subsites": False,
        })

        # Department-specific library
        sources.append({
            "type": "sharepoint_site",
            "url": f"{base_site}/{manifest.domain}",
            "name": f"{manifest.domain} Department Documents",
            "include_subsites": True,
        })

        # Data source references
        for source_id in manifest.data_source_ids[:10]:  # Limit
            sources.append({
                "type": "dataverse_table",
                "name": f"Data: {source_id}",
                "reference": source_id,
            })

        return sources

    def _generate_manual_steps(
        self, manifest: Any, platform_config: PlatformConfig
    ) -> list[str]:
        """Generate manual deployment steps."""
        return [
            "1. Open Copilot Studio (https://copilotstudio.microsoft.com)",
            f"2. Select environment: {platform_config.environment}",
            "3. Create new Copilot or import solution",
            f"4. Set name to: {manifest.name}",
            "5. Configure system message (see config)",
            "6. Create Topics from the topics configuration",
            "7. Connect SharePoint knowledge sources",
            "8. Enable generative answers",
            "9. Configure authentication (Azure AD recommended)",
            "10. Add to Teams channel for testing",
            "11. Configure DLP policy inheritance",
            "12. Publish and test",
        ]

    def _generate_api_calls(
        self, config: dict, deployment_config: dict
    ) -> list[dict[str, Any]]:
        """Generate Power Platform API calls for automated deployment."""
        return [
            {
                "step": "create_solution",
                "method": "POST",
                "endpoint": "/api/data/v9.2/solutions",
                "body": {
                    "uniquename": deployment_config["solution"],
                    "friendlyname": config["name"],
                    "version": "1.0.0.0",
                },
            },
            {
                "step": "create_bot",
                "method": "POST",
                "endpoint": "/api/data/v9.2/bots",
                "body": {
                    "name": config["name"],
                    "description": config["description"],
                    "schemaname": config["name"].replace(" ", "_").lower(),
                },
            },
            {
                "step": "configure_system_message",
                "method": "PATCH",
                "endpoint": "/api/data/v9.2/bots({bot_id})",
                "body": {
                    "systemmessage": config["system_message"],
                },
            },
        ]

    def _generate_export_files(self, config: dict) -> list[dict[str, Any]]:
        """Generate files for solution export/import."""
        return [
            {
                "name": f"{config['name'].replace(' ', '_')}_solution.zip",
                "type": "copilot_solution",
                "description": "Power Platform solution package",
            },
            {
                "name": f"{config['name'].replace(' ', '_')}_topics.json",
                "type": "topics_export",
                "content": config.get("topics", []),
            },
            {
                "name": f"{config['name'].replace(' ', '_')}_config.json",
                "type": "configuration",
                "content": config,
            },
        ]

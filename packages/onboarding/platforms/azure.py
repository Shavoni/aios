"""Azure OpenAI Assistants adapter.

Enterprise-grade deployment with full instruction support (256K chars).
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


class AzureAssistantsAdapter(PlatformAdapter):
    """Adapter for Azure OpenAI Assistants API."""

    platform = PlatformType.AZURE_ASSISTANTS

    def get_constraints(self) -> dict[str, Any]:
        """Get Azure Assistants constraints."""
        return PLATFORM_CONSTRAINTS["azure_assistants"]

    def adapt(
        self,
        manifest: Any,
        platform_config: PlatformConfig,
    ) -> AgentOutput:
        """Convert agent manifest to Azure OpenAI Assistants format."""
        constraints = self.get_constraints()
        warnings = []

        # Build name (max 256 chars - generous)
        name = self.truncate(manifest.name, constraints["name"]["max_chars"])

        # Build description (max 512 chars)
        description = self._build_description(manifest, constraints["description"]["max_chars"])

        # Build instructions (max 256000 chars - can use full HAAIS template!)
        instructions = self._build_full_instructions(manifest)

        # Prepare tools
        tools = self._prepare_tools(manifest)

        # Prepare file search configuration
        file_search_config = self._prepare_file_search(manifest)

        # Get conversation starters (for frontend integration)
        starters = get_starters_for_department(
            manifest.id,
            "azure_assistants",
            manifest.name,
        )

        # Build the Assistant configuration
        config = {
            "name": name,
            "description": description,
            "instructions": instructions,
            "model": platform_config.azure_deployment_name or "gpt-4-turbo",
            "tools": tools,
            "file_ids": [],  # Populated after file upload
            "metadata": {
                "haais_agent_id": manifest.id,
                "domain": manifest.domain,
                "sensitivity": manifest.sensitivity,
                "escalates_to": manifest.escalates_to,
                "version": "1.0.0",
            },
        }

        # Azure-specific deployment configuration
        deployment_config = {
            "subscription_id": platform_config.azure_subscription_id,
            "resource_group": platform_config.azure_resource_group,
            "openai_endpoint": platform_config.azure_openai_endpoint,
            "deployment_name": platform_config.azure_deployment_name,
        }

        # API calls for automated deployment
        api_calls = self._generate_api_calls(config, deployment_config, file_search_config)

        # Manual steps if API deployment not configured
        manual_steps = self._generate_manual_steps(manifest, platform_config)

        return AgentOutput(
            platform=self.platform,
            agent_id=manifest.id,
            agent_name=name,
            config={
                **config,
                "deployment": deployment_config,
                "file_search": file_search_config,
                "conversation_starters": starters,
            },
            files=self._prepare_knowledge_files(manifest),
            manual_steps=manual_steps,
            warnings=warnings,
            api_calls=api_calls,
        )

    def _build_description(self, manifest: Any, max_chars: int) -> str:
        """Build description for Azure Assistant."""
        desc = f"{manifest.title} - HAAIS-governed AI Leadership Asset for {manifest.domain}. "
        desc += f"Escalates to: {manifest.escalates_to}"
        return self.truncate(desc, max_chars)

    def _build_full_instructions(self, manifest: Any) -> str:
        """Build complete HAAIS instructions.

        Azure supports 256K chars, so we can include the full 8-section template!
        """
        sections = []

        # Section 1: Identity
        sections.append(f"""# SECTION 1: IDENTITY & ROLE

You are **{manifest.name}**, serving as the **{manifest.title}**.

## Core Identity
- **Domain**: {manifest.domain}
- **Governance Level**: {manifest.sensitivity}
- **Escalation Path**: {manifest.escalates_to}

## Description
{manifest.description}

You are a Leadership Asset under the HAAIS (Human Assisted AI Services) governance framework, designed to assist city employees while maintaining appropriate human oversight.""")

        # Section 2: Capabilities
        if manifest.capabilities:
            caps = "\n".join(f"- {c}" for c in manifest.capabilities)
            sections.append(f"""# SECTION 2: CORE COMPETENCIES

## What You Can Help With
{caps}

## Knowledge Domain
You have access to department-specific knowledge bases and can reference:
- Official policies and procedures
- Approved guidance documents
- Historical data and reports (where permitted)
- Standard operating procedures""")

        # Section 3: Guardrails
        if manifest.guardrails:
            rails = "\n".join(f"- **{g}**" for g in manifest.guardrails)
            sections.append(f"""# SECTION 3: GUARDRAILS (MUST FOLLOW)

These guardrails are NON-NEGOTIABLE. Violation triggers automatic escalation.

## Prohibited Actions
{rails}

## Universal Prohibitions
- Never impersonate a city official or make commitments on their behalf
- Never disclose personally identifiable information (PII)
- Never provide legal advice or medical diagnoses
- Never bypass approval workflows
- Never delete or modify official records""")

        # Section 4: HAAIS Governance Framework
        sections.append(f"""# SECTION 4: HAAIS GOVERNANCE FRAMEWORK

## Human-In-The-Loop (HITL) Modes

### INFORM Mode
- **Trigger**: Information requests, explanations, lookups
- **Action**: Provide information directly
- **Audit**: Log query and response

### DRAFT Mode
- **Trigger**: Document creation, communications, reports
- **Action**: Create draft with clear "DRAFT - REQUIRES REVIEW" marking
- **Audit**: Log draft creation, track review status
- **Requirement**: All drafts must be reviewed by appropriate staff before use

### EXECUTE Mode
- **Trigger**: Pre-approved actions with clear parameters
- **Action**: Execute with full audit trail
- **Audit**: Log action, parameters, outcome, reviewer
- **Requirement**: Must have prior approval for the action type

### ESCALATE Mode
- **Trigger**: High-risk requests, policy exceptions, legal/safety matters
- **Action**: Acknowledge, explain escalation, provide contact for {manifest.escalates_to}
- **Audit**: Log escalation reason, route to human queue

## Sensitivity Level: {manifest.sensitivity.upper()}
This agent operates at {manifest.sensitivity} sensitivity, which means:
- {"Strict human review for all outputs" if manifest.sensitivity == "critical" else ""}
- {"Draft mode by default for document creation" if manifest.sensitivity == "high" else ""}
- {"Standard audit logging" if manifest.sensitivity == "medium" else ""}
- {"Streamlined operations with logging" if manifest.sensitivity == "low" else ""}""")

        # Section 5: Response Protocols
        sections.append("""# SECTION 5: RESPONSE PROTOCOLS

## Opening
- Acknowledge the request
- Confirm understanding if complex
- State your capability to help (or limitations)

## Information Delivery
- Lead with the most important information
- Use clear, concise language appropriate for government staff
- Cite sources when referencing policies or data
- Provide context for nuanced topics

## Draft Creation
- Always mark as "DRAFT - REQUIRES REVIEW"
- Include placeholders for required customization [BRACKETS]
- Note any assumptions made
- Suggest review checklist

## Escalation
- Acknowledge the request respectfully
- Explain why escalation is needed (without being alarming)
- Provide specific contact: {manifest.escalates_to}
- Offer to help prepare materials for the escalated conversation

## Closing
- Summarize key points if complex
- Offer to clarify or assist further
- Remind of draft review requirements if applicable""")

        # Section 6: Knowledge Hierarchy
        sections.append("""# SECTION 6: KNOWLEDGE HIERARCHY

When information conflicts, prioritize in this order:

1. **Federal Law & Regulations** (always supreme)
2. **State Law & Regulations**
3. **City Charter** (constitutional document)
4. **City Ordinances** (legislative acts)
5. **Administrative Policies** (Mayor/Director-level)
6. **Department Procedures** (operational guidance)
7. **Best Practices** (industry standards)

Always cite the level of authority when providing guidance.""")

        # Section 7: Error Handling
        sections.append(f"""# SECTION 7: ERROR HANDLING & UNCERTAINTY

## When Uncertain
- Acknowledge uncertainty explicitly
- Provide what you do know with confidence levels
- Suggest verification steps
- Offer to escalate if stakes are high

## When Information is Unavailable
- State clearly what information you cannot access
- Suggest where it might be found
- Offer alternative assistance

## When Asked Beyond Scope
- Politely redirect to appropriate resource
- For other departments: suggest the correct Leadership Asset
- For external matters: provide appropriate external contacts
- Never guess or speculate on matters outside your domain""")

        # Section 8: Special Protocols
        sections.append(f"""# SECTION 8: SPECIAL PROTOCOLS

## Emergency Situations
If a message indicates an emergency:
1. Immediately direct to appropriate emergency services
2. Do NOT attempt to provide emergency guidance
3. Log the interaction for follow-up

## Media Inquiries
All media inquiries must be escalated to Communications/Public Affairs.
Response: "Media inquiries are handled by our Communications team. Please contact [Communications Office] at [contact]."

## Legal Matters
Any request that may involve legal liability, litigation, or legal interpretation:
Response: "This matter requires review by the Law Department. Please contact [City Attorney's Office]."

## Elected Officials
Requests from or about elected officials require special handling:
- Verify the nature of the request
- Route appropriately based on content
- Log all interactions

## Audit & Compliance
All interactions are logged for:
- Quality assurance
- Compliance monitoring
- Training improvement
- Legal defensibility""")

        return "\n\n".join(sections)

    def _prepare_tools(self, manifest: Any) -> list[dict[str, Any]]:
        """Prepare tools configuration for Azure Assistant."""
        tools = [
            {"type": "file_search"},  # Enable RAG
        ]

        # Add code interpreter for data analysis capabilities
        if manifest.domain in ["Finance", "Analytics", "Strategy"]:
            tools.append({"type": "code_interpreter"})

        return tools

    def _prepare_file_search(self, manifest: Any) -> dict[str, Any]:
        """Prepare file search (vector store) configuration."""
        return {
            "vector_store_name": f"{manifest.id}_knowledge_base",
            "chunking_strategy": {
                "type": "auto",
            },
            "file_types": [".pdf", ".md", ".txt", ".docx", ".json"],
        }

    def _prepare_knowledge_files(self, manifest: Any) -> list[dict[str, Any]]:
        """Prepare knowledge files for upload."""
        files = [
            {
                "name": "HAAIS_Governance_Framework.md",
                "type": "governance",
                "required": True,
            },
            {
                "name": f"{manifest.domain}_Policies.md",
                "type": "department_policies",
                "required": True,
            },
        ]

        # Add data source references
        for source_id in manifest.data_source_ids:
            files.append({
                "name": f"data_{source_id}.json",
                "type": "data_reference",
                "source_id": source_id,
            })

        return files

    def _generate_api_calls(
        self,
        config: dict,
        deployment_config: dict,
        file_search_config: dict,
    ) -> list[dict[str, Any]]:
        """Generate Azure OpenAI API calls for deployment."""
        base_url = deployment_config.get("openai_endpoint", "https://{resource}.openai.azure.com")

        return [
            {
                "step": "create_vector_store",
                "method": "POST",
                "endpoint": f"{base_url}/openai/vector_stores?api-version=2024-05-01-preview",
                "body": {
                    "name": file_search_config["vector_store_name"],
                },
            },
            {
                "step": "upload_files",
                "method": "POST",
                "endpoint": f"{base_url}/openai/files?api-version=2024-05-01-preview",
                "note": "Upload each knowledge file with purpose='assistants'",
            },
            {
                "step": "add_files_to_vector_store",
                "method": "POST",
                "endpoint": f"{base_url}/openai/vector_stores/{{vector_store_id}}/files?api-version=2024-05-01-preview",
                "note": "Add uploaded file IDs to vector store",
            },
            {
                "step": "create_assistant",
                "method": "POST",
                "endpoint": f"{base_url}/openai/assistants?api-version=2024-05-01-preview",
                "body": {
                    "name": config["name"],
                    "description": config["description"],
                    "instructions": config["instructions"],
                    "model": config["model"],
                    "tools": config["tools"],
                    "tool_resources": {
                        "file_search": {
                            "vector_store_ids": ["{{vector_store_id}}"],
                        },
                    },
                    "metadata": config["metadata"],
                },
            },
        ]

    def _generate_manual_steps(
        self, manifest: Any, platform_config: PlatformConfig
    ) -> list[str]:
        """Generate manual deployment steps."""
        return [
            "1. Ensure Azure OpenAI resource is provisioned",
            f"2. Deploy model: {platform_config.azure_deployment_name or 'gpt-4-turbo'}",
            "3. Create vector store in Azure OpenAI Studio",
            "4. Upload knowledge files to vector store",
            "5. Create Assistant with configuration",
            "6. Test with sample queries",
            "7. Configure content filtering policies",
            "8. Set up RBAC permissions",
            "9. Enable diagnostic logging",
            "10. Deploy frontend integration",
        ]

"""Google Vertex AI Agents (Dialogflow CX) adapter.

Enterprise conversational AI with multi-language support.
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


class VertexAIAdapter(PlatformAdapter):
    """Adapter for Google Vertex AI Agents (Dialogflow CX)."""

    platform = PlatformType.VERTEX_AI

    def get_constraints(self) -> dict[str, Any]:
        """Get Vertex AI constraints."""
        return PLATFORM_CONSTRAINTS["vertex_ai"]

    def adapt(
        self,
        manifest: Any,
        platform_config: PlatformConfig,
    ) -> AgentOutput:
        """Convert agent manifest to Vertex AI Agent format."""
        constraints = self.get_constraints()
        warnings = []

        # Build display name (max 64 chars)
        display_name = self.truncate(
            manifest.name,
            constraints["display_name_field"]["max_chars"],
        )
        if len(manifest.name) > constraints["display_name_field"]["max_chars"]:
            warnings.append(f"Name truncated to {constraints['display_name_field']['max_chars']} chars")

        # Build description (max 500 chars)
        description = self._build_description(manifest, constraints["description"]["max_chars"])

        # Build system instruction (max 8000 chars for generative AI)
        system_instruction = self._build_system_instruction(
            manifest,
            constraints["generative_ai"]["system_instruction_max_chars"],
        )

        # Generate flows and intents
        flows = self._generate_flows(manifest)
        intents = self._generate_intents(manifest)

        # Get suggestion chips (conversation starters)
        suggestion_chips = get_starters_for_department(
            manifest.id,
            "vertex_ai",
            manifest.name,
        )

        # Knowledge connector configuration
        knowledge_config = self._prepare_knowledge_connectors(manifest, platform_config)

        # Build the agent configuration
        config = {
            "display_name": display_name,
            "description": description,
            "default_language_code": "en",
            "supported_language_codes": ["en", "es"],  # Cleveland has Spanish speakers
            "time_zone": "America/New_York",  # Cleveland timezone
            "start_flow": "Default Start Flow",
            "generative_settings": {
                "model": platform_config.vertex_model,
                "system_instruction": system_instruction,
                "temperature": 0.7,
            },
            "flows": flows,
            "intents": intents,
            "suggestion_chips": suggestion_chips,
            "knowledge_connectors": knowledge_config,
            "security_settings": {
                "redact_pii": True,
                "audit_logging_enabled": True,
            },
            "metadata": {
                "haais_agent_id": manifest.id,
                "domain": manifest.domain,
                "sensitivity": manifest.sensitivity,
                "escalates_to": manifest.escalates_to,
            },
        }

        # Deployment configuration
        deployment_config = {
            "project_id": platform_config.vertex_project_id,
            "location": platform_config.vertex_location,
            "model": platform_config.vertex_model,
        }

        # API calls for deployment
        api_calls = self._generate_api_calls(config, deployment_config)

        # Manual steps
        manual_steps = self._generate_manual_steps(manifest, platform_config)

        return AgentOutput(
            platform=self.platform,
            agent_id=manifest.id,
            agent_name=display_name,
            config={**config, "deployment": deployment_config},
            files=self._generate_export_files(config),
            manual_steps=manual_steps,
            warnings=warnings,
            api_calls=api_calls,
        )

    def _build_description(self, manifest: Any, max_chars: int) -> str:
        """Build description for Vertex AI Agent."""
        desc = f"{manifest.title} - HAAIS-governed AI for {manifest.domain}. "
        desc += f"Escalates to: {manifest.escalates_to}."
        return self.truncate(desc, max_chars)

    def _build_system_instruction(self, manifest: Any, max_chars: int) -> str:
        """Build system instruction for generative AI."""
        sections = []

        # Identity
        sections.append(f"""# IDENTITY

You are {manifest.name}, {manifest.title}.
Domain: {manifest.domain}
Governance Level: {manifest.sensitivity}

{manifest.description}""")

        # Capabilities
        if manifest.capabilities:
            caps = "\n".join(f"- {c}" for c in manifest.capabilities)
            sections.append(f"""# CAPABILITIES

{caps}""")

        # Guardrails
        if manifest.guardrails:
            rails = "\n".join(f"- {g}" for g in manifest.guardrails)
            sections.append(f"""# GUARDRAILS (MUST FOLLOW)

{rails}

Universal Rules:
- Never impersonate city officials
- Never disclose PII
- Never provide legal/medical advice
- Always identify as an AI assistant""")

        # Governance
        sections.append(f"""# HAAIS GOVERNANCE

Human-in-the-Loop Modes:
- INFORM: Provide information directly
- DRAFT: Create drafts for human review
- EXECUTE: Take pre-approved actions
- ESCALATE: Route to {manifest.escalates_to}

Always log interactions for audit purposes.""")

        # Response guidelines
        sections.append("""# RESPONSE GUIDELINES

- Be professional and concise
- Cite sources when referencing policies
- Mark drafts clearly for review
- Acknowledge limitations
- Offer escalation when appropriate""")

        full_instruction = "\n\n".join(sections)

        if len(full_instruction) <= max_chars:
            return full_instruction

        return self.compress_instructions(full_instruction, max_chars)

    def _generate_flows(self, manifest: Any) -> list[dict[str, Any]]:
        """Generate Dialogflow CX flows."""
        flows = []

        # Default Start Flow
        flows.append({
            "name": "Default Start Flow",
            "description": "Initial conversation flow",
            "transition_routes": [
                {
                    "intent": "greeting",
                    "target_page": "Welcome Page",
                },
                {
                    "intent": "information_request",
                    "target_page": "Information Page",
                },
                {
                    "intent": "draft_request",
                    "target_page": "Draft Page",
                },
                {
                    "intent": "escalation_trigger",
                    "target_page": "Escalation Page",
                },
            ],
            "pages": [
                {
                    "name": "Welcome Page",
                    "entry_fulfillment": {
                        "messages": [
                            {
                                "text": f"Hello! I'm {manifest.name}, your {manifest.title}. How can I help you today?"
                            }
                        ],
                        "suggestion_chips": [
                            cap[:50] for cap in (manifest.capabilities or [])[:4]
                        ],
                    },
                },
                {
                    "name": "Information Page",
                    "entry_fulfillment": {
                        "generative_response": True,
                        "knowledge_connector_enabled": True,
                    },
                },
                {
                    "name": "Draft Page",
                    "entry_fulfillment": {
                        "messages": [
                            {
                                "text": "I'll create a draft for your review. Please note this is a DRAFT that requires human approval before use."
                            }
                        ],
                        "generative_response": True,
                    },
                },
                {
                    "name": "Escalation Page",
                    "entry_fulfillment": {
                        "messages": [
                            {
                                "text": f"This request requires human oversight. Please contact {manifest.escalates_to} for assistance. I can help you prepare materials for that conversation."
                            }
                        ],
                    },
                },
            ],
        })

        # Error Handling Flow
        flows.append({
            "name": "Error Handling Flow",
            "description": "Handle errors and fallbacks",
            "pages": [
                {
                    "name": "No Match Page",
                    "entry_fulfillment": {
                        "messages": [
                            {
                                "text": f"I'm not sure I understood that. I specialize in {manifest.domain} matters. Could you rephrase your question?"
                            }
                        ],
                    },
                },
                {
                    "name": "No Input Page",
                    "entry_fulfillment": {
                        "messages": [
                            {
                                "text": "I didn't receive your input. Please try again or let me know how I can help."
                            }
                        ],
                    },
                },
            ],
        })

        return flows

    def _generate_intents(self, manifest: Any) -> list[dict[str, Any]]:
        """Generate intents for the agent."""
        intents = []

        # Greeting intent
        intents.append({
            "name": "greeting",
            "training_phrases": [
                "hello", "hi", "hey", "good morning", "good afternoon",
                "help", "start", "what can you do", "get started",
            ],
        })

        # Information request intent
        intents.append({
            "name": "information_request",
            "training_phrases": [
                "what is", "tell me about", "explain", "how does",
                "information on", "details about", "describe", "show me",
                "what are the", "can you tell me",
            ],
        })

        # Draft request intent
        intents.append({
            "name": "draft_request",
            "training_phrases": [
                "draft", "write", "create", "compose", "prepare",
                "help me write", "generate", "make a", "build",
                "can you draft", "put together",
            ],
        })

        # Escalation trigger intent
        intents.append({
            "name": "escalation_trigger",
            "training_phrases": [
                "legal", "lawsuit", "attorney", "confidential",
                "personnel action", "termination", "discipline",
                "emergency", "urgent", "media", "press", "complaint",
                "speak to a human", "talk to someone", "supervisor",
            ],
        })

        # Fallback intent
        intents.append({
            "name": "fallback",
            "is_fallback": True,
            "training_phrases": [],
        })

        return intents

    def _prepare_knowledge_connectors(
        self, manifest: Any, platform_config: PlatformConfig
    ) -> list[dict[str, Any]]:
        """Prepare knowledge connector configuration."""
        connectors = []

        # Cloud Storage connector for governance docs
        connectors.append({
            "type": "cloud_storage",
            "display_name": "HAAIS Governance",
            "bucket": f"gs://{platform_config.vertex_project_id}-knowledge/governance",
            "file_types": ["pdf", "txt", "html"],
        })

        # Department-specific knowledge
        connectors.append({
            "type": "cloud_storage",
            "display_name": f"{manifest.domain} Documents",
            "bucket": f"gs://{platform_config.vertex_project_id}-knowledge/{manifest.domain.lower()}",
            "file_types": ["pdf", "txt", "html", "docx"],
        })

        # Data source references
        for source_id in manifest.data_source_ids[:5]:
            connectors.append({
                "type": "bigquery",
                "display_name": f"Data: {source_id}",
                "dataset": f"{platform_config.vertex_project_id}.city_data",
                "table": source_id,
            })

        return connectors

    def _generate_api_calls(
        self, config: dict, deployment_config: dict
    ) -> list[dict[str, Any]]:
        """Generate Dialogflow CX API calls for deployment."""
        project = deployment_config.get("project_id", "PROJECT_ID")
        location = deployment_config.get("location", "us-central1")
        base_url = f"https://{location}-dialogflow.googleapis.com/v3"

        return [
            {
                "step": "create_agent",
                "method": "POST",
                "endpoint": f"{base_url}/projects/{project}/locations/{location}/agents",
                "body": {
                    "displayName": config["display_name"],
                    "defaultLanguageCode": config["default_language_code"],
                    "supportedLanguageCodes": config["supported_language_codes"],
                    "timeZone": config["time_zone"],
                    "description": config["description"],
                    "securitySettings": config["security_settings"],
                },
            },
            {
                "step": "configure_generative_settings",
                "method": "PATCH",
                "endpoint": f"{base_url}/projects/{project}/locations/{location}/agents/{{agent_id}}/generativeSettings",
                "body": config["generative_settings"],
            },
            {
                "step": "create_intents",
                "method": "POST",
                "endpoint": f"{base_url}/projects/{project}/locations/{location}/agents/{{agent_id}}/intents",
                "note": "Create each intent from the intents configuration",
                "body_template": "intents",
            },
            {
                "step": "create_flows",
                "method": "POST",
                "endpoint": f"{base_url}/projects/{project}/locations/{location}/agents/{{agent_id}}/flows",
                "note": "Create each flow from the flows configuration",
                "body_template": "flows",
            },
            {
                "step": "configure_knowledge",
                "method": "POST",
                "endpoint": f"{base_url}/projects/{project}/locations/{location}/agents/{{agent_id}}/knowledgeBases",
                "note": "Set up knowledge connectors",
                "body_template": "knowledge_connectors",
            },
        ]

    def _generate_manual_steps(
        self, manifest: Any, platform_config: PlatformConfig
    ) -> list[str]:
        """Generate manual deployment steps."""
        return [
            "1. Open Google Cloud Console",
            f"2. Navigate to Dialogflow CX in project: {platform_config.vertex_project_id}",
            f"3. Create new agent in location: {platform_config.vertex_location}",
            f"4. Set display name to: {manifest.name}",
            "5. Configure default language (English) and timezone (America/New_York)",
            "6. Import flows and intents from configuration",
            "7. Set up knowledge connectors:",
            "   - Cloud Storage for governance docs",
            "   - Cloud Storage for department docs",
            "   - BigQuery for data sources (if applicable)",
            "8. Configure generative AI settings",
            f"   - Model: {platform_config.vertex_model}",
            "   - System instruction: (from config)",
            "9. Enable security settings (PII redaction, audit logging)",
            "10. Test with sample conversations",
            "11. Deploy to desired channels (web, telephony, etc.)",
        ]

    def _generate_export_files(self, config: dict) -> list[dict[str, Any]]:
        """Generate files for agent export."""
        return [
            {
                "name": f"{config['display_name'].replace(' ', '_')}_agent.json",
                "type": "dialogflow_cx_agent",
                "content": config,
            },
            {
                "name": f"{config['display_name'].replace(' ', '_')}_intents.json",
                "type": "intents_export",
                "content": config.get("intents", []),
            },
            {
                "name": f"{config['display_name'].replace(' ', '_')}_flows.json",
                "type": "flows_export",
                "content": config.get("flows", []),
            },
        ]

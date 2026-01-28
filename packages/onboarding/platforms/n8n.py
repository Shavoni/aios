"""N8N AI Workflow adapter.

Flexible automation platform for custom integrations.
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


class N8NAdapter(PlatformAdapter):
    """Adapter for N8N AI Workflows."""

    platform = PlatformType.N8N

    def get_constraints(self) -> dict[str, Any]:
        """Get N8N constraints."""
        return PLATFORM_CONSTRAINTS["n8n"]

    def adapt(
        self,
        manifest: Any,
        platform_config: PlatformConfig,
    ) -> AgentOutput:
        """Convert agent manifest to N8N workflow format."""
        constraints = self.get_constraints()
        warnings = []

        # Build workflow name (max 128 chars)
        name = self.truncate(
            f"{manifest.name} - HAAIS Agent",
            constraints["workflow_name"]["max_chars"],
        )

        # Build system message (up to 32K chars practical limit)
        system_message = self._build_system_message(manifest)

        # Prepare tools configuration
        tools = self._prepare_tools(manifest)

        # Get conversation starters
        starters = get_starters_for_department(
            manifest.id,
            "n8n",
            manifest.name,
        )

        # Build the N8N workflow configuration
        config = {
            "name": name,
            "description": manifest.description,
            "nodes": self._generate_workflow_nodes(manifest, platform_config, system_message),
            "connections": self._generate_connections(),
            "settings": {
                "executionOrder": "v1",
                "saveDataSuccessExecution": "all",
                "saveDataErrorExecution": "all",
            },
            "meta": {
                "haais_agent_id": manifest.id,
                "domain": manifest.domain,
                "sensitivity": manifest.sensitivity,
                "escalates_to": manifest.escalates_to,
            },
            "conversation_starters": starters,
            "tools": tools,
        }

        # Deployment configuration
        deployment_config = {
            "instance_url": platform_config.n8n_instance_url,
            "webhook_base": platform_config.n8n_webhook_base,
            "vector_store": platform_config.n8n_vector_store,
        }

        # Generate API calls for automated deployment
        api_calls = self._generate_api_calls(config, deployment_config)

        # Manual steps
        manual_steps = self._generate_manual_steps(manifest, platform_config)

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

    def _build_system_message(self, manifest: Any) -> str:
        """Build system message for the AI Agent node."""
        sections = []

        # Identity
        sections.append(f"""# IDENTITY & ROLE

You are **{manifest.name}**, serving as the **{manifest.title}**.

## Core Identity
- **Domain**: {manifest.domain}
- **Governance Level**: {manifest.sensitivity}
- **Escalation Path**: {manifest.escalates_to}

## Description
{manifest.description}

You operate under HAAIS (Human Assisted AI Services) governance framework.""")

        # Capabilities
        if manifest.capabilities:
            caps = "\n".join(f"- {c}" for c in manifest.capabilities)
            sections.append(f"""# CAPABILITIES

## What You Can Help With
{caps}""")

        # Guardrails
        if manifest.guardrails:
            rails = "\n".join(f"- **{g}**" for g in manifest.guardrails)
            sections.append(f"""# GUARDRAILS (MUST FOLLOW)

These guardrails are NON-NEGOTIABLE:

{rails}

## Universal Prohibitions
- Never impersonate a city official
- Never disclose PII
- Never provide legal advice or medical diagnoses
- Never bypass approval workflows""")

        # HITL Modes
        sections.append(f"""# HUMAN-IN-THE-LOOP MODES

## INFORM Mode
Provide information directly with logging.

## DRAFT Mode
Create drafts marked "DRAFT - REQUIRES REVIEW" for human approval.

## EXECUTE Mode
Execute pre-approved actions with full audit trail.

## ESCALATE Mode
Route to {manifest.escalates_to} for high-risk matters.""")

        # Response guidelines
        sections.append("""# RESPONSE GUIDELINES

- Be concise and professional
- Cite sources when referencing policies
- Mark all drafts clearly for review
- Acknowledge limitations transparently
- Always identify as an AI assistant""")

        return "\n\n".join(sections)

    def _prepare_tools(self, manifest: Any) -> list[dict[str, Any]]:
        """Prepare tools for the AI Agent node."""
        tools = []

        # Add vector store retrieval tool
        tools.append({
            "name": "knowledge_retrieval",
            "type": "vector_store_retrieval",
            "description": f"Retrieve relevant information from {manifest.domain} knowledge base",
        })

        # Add HTTP tool for API integrations
        tools.append({
            "name": "api_integration",
            "type": "http_request",
            "description": "Make API calls to connected city systems",
        })

        # Add code execution for data analysis
        if manifest.domain in ["Finance", "Analytics", "Strategy"]:
            tools.append({
                "name": "data_analysis",
                "type": "code",
                "description": "Execute Python code for data analysis",
            })

        return tools

    def _generate_workflow_nodes(
        self,
        manifest: Any,
        platform_config: PlatformConfig,
        system_message: str,
    ) -> list[dict[str, Any]]:
        """Generate N8N workflow nodes."""
        nodes = []

        # 1. Webhook Trigger
        nodes.append({
            "id": "webhook_trigger",
            "name": "Webhook Trigger",
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 1.1,
            "position": [250, 300],
            "parameters": {
                "path": f"haais/{manifest.id}",
                "httpMethod": "POST",
                "responseMode": "responseNode",
                "options": {},
            },
        })

        # 2. Memory Node (conversation history)
        nodes.append({
            "id": "memory",
            "name": "Window Buffer Memory",
            "type": "@n8n/n8n-nodes-langchain.memoryBufferWindow",
            "typeVersion": 1.2,
            "position": [450, 500],
            "parameters": {
                "sessionKey": "={{ $json.session_id }}",
                "windowSize": 10,
            },
        })

        # 3. Vector Store Retriever
        vector_store_type = self._get_vector_store_node(platform_config.n8n_vector_store)
        nodes.append({
            "id": "vector_retriever",
            "name": "Vector Store Retriever",
            "type": vector_store_type,
            "typeVersion": 1,
            "position": [450, 400],
            "parameters": {
                "topK": 5,
            },
        })

        # 4. AI Agent Node
        nodes.append({
            "id": "ai_agent",
            "name": f"{manifest.name} Agent",
            "type": "@n8n/n8n-nodes-langchain.agent",
            "typeVersion": 1.6,
            "position": [650, 300],
            "parameters": {
                "text": "={{ $json.message }}",
                "options": {
                    "systemMessage": system_message,
                },
            },
        })

        # 5. LLM Model (configurable)
        nodes.append({
            "id": "llm_model",
            "name": "OpenAI Chat Model",
            "type": "@n8n/n8n-nodes-langchain.lmChatOpenAi",
            "typeVersion": 1,
            "position": [650, 500],
            "parameters": {
                "model": "gpt-4-turbo",
                "options": {
                    "temperature": 0.7,
                },
            },
        })

        # 6. Audit Logger
        nodes.append({
            "id": "audit_log",
            "name": "Audit Logger",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.1,
            "position": [850, 400],
            "parameters": {
                "method": "POST",
                "url": "={{ $env.AUDIT_ENDPOINT }}/log",
                "sendBody": True,
                "bodyParameters": {
                    "parameters": [
                        {"name": "agent_id", "value": manifest.id},
                        {"name": "domain", "value": manifest.domain},
                        {"name": "query", "value": "={{ $('Webhook Trigger').item.json.message }}"},
                        {"name": "response", "value": "={{ $json.output }}"},
                        {"name": "timestamp", "value": "={{ $now.toISO() }}"},
                    ],
                },
            },
        })

        # 7. Response Node
        nodes.append({
            "id": "response",
            "name": "Respond to Webhook",
            "type": "n8n-nodes-base.respondToWebhook",
            "typeVersion": 1,
            "position": [1050, 300],
            "parameters": {
                "respondWith": "json",
                "responseBody": "={{ { response: $('AI Agent').item.json.output, agent_id: '" + manifest.id + "', timestamp: $now.toISO() } }}",
            },
        })

        return nodes

    def _get_vector_store_node(self, store_type: str) -> str:
        """Get the appropriate vector store node type."""
        store_nodes = {
            "pinecone": "@n8n/n8n-nodes-langchain.vectorStorePinecone",
            "qdrant": "@n8n/n8n-nodes-langchain.vectorStoreQdrant",
            "supabase": "@n8n/n8n-nodes-langchain.vectorStoreSupabase",
            "postgres": "@n8n/n8n-nodes-langchain.vectorStorePGVector",
            "in_memory": "@n8n/n8n-nodes-langchain.vectorStoreInMemory",
        }
        return store_nodes.get(store_type, store_nodes["in_memory"])

    def _generate_connections(self) -> dict[str, Any]:
        """Generate node connections."""
        return {
            "webhook_trigger": {
                "main": [[{"node": "ai_agent", "type": "main", "index": 0}]]
            },
            "memory": {
                "ai_memory": [[{"node": "ai_agent", "type": "ai_memory", "index": 0}]]
            },
            "vector_retriever": {
                "ai_tool": [[{"node": "ai_agent", "type": "ai_tool", "index": 0}]]
            },
            "llm_model": {
                "ai_languageModel": [[{"node": "ai_agent", "type": "ai_languageModel", "index": 0}]]
            },
            "ai_agent": {
                "main": [[{"node": "audit_log", "type": "main", "index": 0}]]
            },
            "audit_log": {
                "main": [[{"node": "response", "type": "main", "index": 0}]]
            },
        }

    def _generate_api_calls(
        self, config: dict, deployment_config: dict
    ) -> list[dict[str, Any]]:
        """Generate N8N API calls for deployment."""
        base_url = deployment_config.get("instance_url", "http://localhost:5678")

        return [
            {
                "step": "create_workflow",
                "method": "POST",
                "endpoint": f"{base_url}/api/v1/workflows",
                "body": {
                    "name": config["name"],
                    "nodes": config["nodes"],
                    "connections": config["connections"],
                    "settings": config["settings"],
                    "meta": config["meta"],
                },
            },
            {
                "step": "activate_workflow",
                "method": "PATCH",
                "endpoint": f"{base_url}/api/v1/workflows/{{workflow_id}}",
                "body": {
                    "active": True,
                },
            },
        ]

    def _generate_manual_steps(
        self, manifest: Any, platform_config: PlatformConfig
    ) -> list[str]:
        """Generate manual deployment steps."""
        return [
            "1. Open N8N instance (self-hosted or cloud)",
            "2. Import the workflow JSON file",
            "3. Configure credentials:",
            "   - OpenAI API key (or Azure OpenAI)",
            f"   - Vector store credentials ({platform_config.n8n_vector_store})",
            "   - Audit endpoint (if using external logging)",
            "4. Set up the vector store with knowledge documents",
            "5. Configure webhook authentication if needed",
            "6. Activate the workflow",
            "7. Test with sample queries",
            "8. Set up monitoring and error notifications",
        ]

    def _generate_export_files(self, config: dict) -> list[dict[str, Any]]:
        """Generate files for workflow export."""
        return [
            {
                "name": f"{config['name'].replace(' ', '_')}_workflow.json",
                "type": "n8n_workflow",
                "content": config,
            },
            {
                "name": f"{config['name'].replace(' ', '_')}_credentials_template.json",
                "type": "credentials_template",
                "content": {
                    "openai": {"api_key": "YOUR_OPENAI_API_KEY"},
                    "vector_store": {"connection_string": "YOUR_VECTOR_STORE_CONNECTION"},
                },
            },
        ]

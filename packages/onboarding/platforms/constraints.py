"""Platform constraints and parameter limits.

Comprehensive reference for each AI platform's capabilities and limitations.
"""

from typing import Any

PLATFORM_CONSTRAINTS: dict[str, dict[str, Any]] = {
    # =========================================================================
    # ChatGPT Custom GPTs
    # =========================================================================
    "chatgpt": {
        "display_name": "ChatGPT Custom GPTs",
        "vendor": "OpenAI",
        "best_for": "Quick deployment, public-facing, demos",
        "requires": "ChatGPT Team or Enterprise subscription",

        "name": {
            "max_chars": 50,
        },
        "description": {
            "max_chars": 300,
            "purpose": "Appears in GPT store and share links",
        },
        "instructions": {
            "max_chars": 8000,
            "purpose": "System prompt - core behavior definition",
        },
        "knowledge_files": {
            "max_count": 20,
            "max_size_per_file_mb": 512,
            "supported_formats": [".md", ".txt", ".pdf", ".docx", ".csv", ".json"],
            "total_max_size_gb": 10,
        },
        "conversation_starters": {
            "max_count": 4,
            "max_chars_each": 100,
            "purpose": "Suggested prompts shown to users",
        },
        "capabilities": {
            "web_browsing": {"supported": True, "default": False},
            "dall_e": {"supported": True, "default": False},
            "code_interpreter": {"supported": True, "default": True},
        },
        "actions": {
            "type": "OpenAPI schema",
            "max_actions": 30,
            "auth_types": ["none", "api_key", "oauth"],
        },
        "visibility_options": ["private", "anyone_with_link", "public"],
        "api_deployment": False,  # Manual creation required
    },

    # =========================================================================
    # Microsoft Copilot Studio
    # =========================================================================
    "copilot_studio": {
        "display_name": "Microsoft Copilot Studio",
        "vendor": "Microsoft",
        "best_for": "Microsoft 365 environments, Teams integration",
        "requires": "Microsoft 365 with Copilot Studio license",

        "name": {
            "max_chars": 100,
        },
        "description": {
            "max_chars": 1000,
        },
        "instructions": {
            "max_chars": 6000,
            "note": "Called 'System message' in Copilot Studio",
        },
        "knowledge_sources": {
            "types": [
                "sharepoint_sites",
                "dataverse_tables",
                "public_websites",
                "uploaded_files",
            ],
            "file_formats": [".pdf", ".docx", ".pptx", ".txt", ".html"],
            "max_file_size_mb": 512,
            "max_total_sources": 20,
        },
        "topics": {
            "purpose": "Conversation flows / intents",
            "max_topics": 1000,
            "trigger_phrases_per_topic": 15,
        },
        "conversation_starters": {
            "max_count": 6,
            "called": "Suggested actions",
        },
        "capabilities": {
            "generative_answers": {"supported": True, "default": True},
            "plugins": {"supported": True, "note": "Power Platform connectors"},
            "power_automate_flows": {"supported": True, "default": False},
        },
        "authentication": {
            "types": ["no_auth", "azure_ad", "generic_oauth"],
            "default": "azure_ad",
        },
        "channels": {
            "supported": ["teams", "web", "facebook", "custom"],
            "default": ["teams", "web"],
        },
        "governance": {
            "dlp_policies": "Inherits from Power Platform",
            "audit_logs": "Microsoft Purview",
        },
        "api_deployment": True,  # Can be deployed via Power Platform CLI
    },

    # =========================================================================
    # Azure OpenAI Assistants
    # =========================================================================
    "azure_assistants": {
        "display_name": "Azure OpenAI Assistants",
        "vendor": "Microsoft Azure",
        "best_for": "Enterprise security, custom deployments, high-volume",
        "requires": "Azure subscription with OpenAI access",

        "name": {
            "max_chars": 256,
        },
        "description": {
            "max_chars": 512,
        },
        "instructions": {
            "max_chars": 256000,  # Much larger than ChatGPT
            "note": "Full instruction sets supported",
        },
        "model": {
            "options": ["gpt-4", "gpt-4-turbo", "gpt-4o", "gpt-35-turbo"],
            "default": "gpt-4-turbo",
            "deployment_required": True,
        },
        "tools": {
            "types": ["code_interpreter", "file_search", "function_calling"],
            "max_tools": 128,
        },
        "file_search": {
            "max_files": 10000,
            "max_file_size_mb": 512,
            "vector_stores": "automatic",
            "supported_formats": [".pdf", ".md", ".txt", ".docx", ".json", ".csv"],
        },
        "code_interpreter": {
            "max_files": 20,
            "max_file_size_mb": 512,
        },
        "function_calling": {
            "max_functions": 128,
            "schema": "JSON Schema",
        },
        "threads": {
            "purpose": "Conversation sessions",
            "max_messages": "unlimited",
            "context_window": "128K for GPT-4 Turbo",
        },
        "governance": {
            "content_filtering": "Azure AI Content Safety",
            "rbac": "Azure IAM",
            "private_endpoints": True,
            "data_residency": "configurable",
        },
        "conversation_starters": {
            "max_count": 10,
            "note": "Defined in application layer",
        },
        "api_deployment": True,  # Full API support
    },

    # =========================================================================
    # Google Vertex AI Agents (Dialogflow CX)
    # =========================================================================
    "vertex_ai": {
        "display_name": "Google Vertex AI Agents",
        "vendor": "Google Cloud",
        "best_for": "Google Workspace environments, multi-language support",
        "requires": "Google Cloud Platform project",

        "display_name_field": {
            "max_chars": 64,
        },
        "description": {
            "max_chars": 500,
        },
        "default_language": "en",
        "supported_languages": "30+",
        "flows": {
            "purpose": "Conversation paths",
            "max_flows": 50,
            "pages_per_flow": 500,
        },
        "intents": {
            "max_intents": 2000,
            "training_phrases_per_intent": 2000,
        },
        "knowledge_connectors": {
            "types": [
                "cloud_storage",
                "bigquery",
                "public_urls",
                "uploaded_documents",
            ],
            "supported_formats": [".pdf", ".html", ".txt", ".csv"],
            "max_documents_per_kb": 50,
        },
        "generative_ai": {
            "model": ["text-bison", "gemini-pro"],
            "system_instruction_max_chars": 8000,
        },
        "conversation_starters": {
            "called": "Suggestion chips",
            "max_count": 10,
        },
        "integrations": {
            "supported": ["web", "telephony", "slack", "teams", "custom"],
        },
        "authentication": {
            "types": ["google_auth", "oauth", "api_key"],
        },
        "api_deployment": True,
    },

    # =========================================================================
    # N8N AI Workflows
    # =========================================================================
    "n8n": {
        "display_name": "N8N AI Workflows",
        "vendor": "N8N (Open Source / Cloud)",
        "best_for": "Automation, multi-system integration, custom workflows",
        "requires": "N8N instance (self-hosted or cloud)",

        "workflow_name": {
            "max_chars": 128,
        },
        "description": {
            "max_chars": "unlimited",
        },
        "ai_agent_node": {
            "type": "AI Agent",
            "supported_models": [
                "openai_gpt4",
                "anthropic_claude",
                "google_gemini",
                "azure_openai",
                "ollama_local",
            ],
            "system_message_max_chars": 32000,  # Practical limit
        },
        "tools": {
            "max_tools": 50,
            "types": ["http_request", "code", "database", "other_n8n_nodes"],
        },
        "knowledge": {
            "via": "Vector Store nodes",
            "supported_stores": [
                "pinecone",
                "qdrant",
                "supabase",
                "postgres_pgvector",
                "in_memory",
            ],
            "document_loaders": [".pdf", ".docx", ".txt", ".csv", ".json", ".html"],
        },
        "memory": {
            "types": ["buffer", "window", "summary", "postgres", "redis"],
        },
        "triggers": {
            "types": ["webhook", "schedule", "manual", "event"],
        },
        "output_channels": {
            "via": "Subsequent nodes",
            "examples": ["slack", "teams", "email", "http_response", "database"],
        },
        "deployment": {
            "self_hosted": True,
            "cloud": True,
        },
        "conversation_starters": {
            "max_count": 10,
            "note": "Defined in frontend application",
        },
        "api_deployment": True,  # Via N8N API
    },
}


# Conversation starter templates by department
STARTER_TEMPLATES: dict[str, list[str]] = {
    "public-health": [
        "What are the current disease surveillance trends?",
        "Show me restaurant inspection failure rates by ward",
        "Draft a community health assessment for [neighborhood]",
        "What CDC guidelines apply to lead abatement?",
    ],
    "hr": [
        "What is the policy on remote work arrangements?",
        "Show me the steps for posting a new position",
        "Draft a communication about benefits enrollment",
        "What are the civil service rules for promotions?",
    ],
    "finance": [
        "What approvals are needed for purchases over $10,000?",
        "Show me the current budget status for [department]",
        "Draft a vendor payment justification memo",
        "What are the procurement card limits and rules?",
    ],
    "building": [
        "What permits are required for a deck addition?",
        "Show me code violation trends by neighborhood",
        "Draft a notice of violation for [address]",
        "What are the lead-safe certification requirements?",
    ],
    "311": [
        "What is the SLA for pothole repairs?",
        "Show me service request volume by category",
        "Draft a response for a repeat complaint",
        "What is the escalation path for unresolved issues?",
    ],
    "strategy": [
        "What is the status of current AI pilot projects?",
        "Compare our governance model to NIST AI RMF",
        "Draft a City Council presentation on HAAIS benefits",
        "What are the What Works Cities requirements?",
    ],
    "public-safety": [
        "What are the crime statistics for my district this month?",
        "Show me the consent decree compliance status",
        "Draft a community meeting presentation on safety",
        "What is the department policy on de-escalation?",
    ],
    "parks": [
        "What programs are available at [recreation center]?",
        "Show me facility utilization rates this quarter",
        "Draft a proposal for a new youth sports league",
        "What is the maintenance schedule for [park]?",
    ],
    "public-works": [
        "What is the current water quality status?",
        "Show me the capital improvement project timeline",
        "Draft a report on outage response times",
        "What are the EPA compliance requirements?",
    ],
    "gcp": [
        "What regional initiatives align with city goals?",
        "Show me cross-sector partnership opportunities",
        "Draft talking points for intergovernmental meeting",
        "What workforce development programs are available?",
    ],
}


def get_starters_for_department(
    department_id: str,
    platform: str,
    official_name: str | None = None,
) -> list[str]:
    """Get conversation starters appropriate for platform limits."""
    templates = STARTER_TEMPLATES.get(
        department_id,
        STARTER_TEMPLATES.get("strategy", [])  # Default fallback
    )

    # Get platform limit
    constraints = PLATFORM_CONSTRAINTS.get(platform, {})
    starter_config = constraints.get("conversation_starters", {})
    max_count = starter_config.get("max_count", 4)

    starters = templates[:max_count]

    # Personalize if official name provided
    if official_name:
        starters = [s.replace("[official]", official_name) for s in starters]

    return starters

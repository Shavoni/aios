"""Platform-agnostic agent generation for multiple AI platforms.

Supports:
- Microsoft Copilot Studio (Primary for M365 environments)
- ChatGPT Custom GPTs (Demos and public-facing)
- Azure OpenAI Assistants (Enterprise security)
- Google Vertex AI Agents (Google Workspace environments)
- N8N Workflows (Automation and integration)
"""

from packages.onboarding.platforms.base import (
    PlatformAdapter,
    PlatformConfig,
    PlatformType,
    AgentOutput,
)
from packages.onboarding.platforms.chatgpt import ChatGPTAdapter
from packages.onboarding.platforms.copilot import CopilotStudioAdapter
from packages.onboarding.platforms.azure import AzureAssistantsAdapter
from packages.onboarding.platforms.n8n import N8NAdapter
from packages.onboarding.platforms.vertex import VertexAIAdapter
from packages.onboarding.platforms.constraints import (
    PLATFORM_CONSTRAINTS,
    STARTER_TEMPLATES,
    get_starters_for_department,
)
from packages.onboarding.platforms.adapters import (
    get_adapter,
    generate_for_platform,
    generate_for_all_platforms,
    get_available_platforms,
    get_platform_constraints,
    compare_platforms,
)

__all__ = [
    # Base classes
    "PlatformAdapter",
    "PlatformConfig",
    "PlatformType",
    "AgentOutput",
    # Adapters
    "ChatGPTAdapter",
    "CopilotStudioAdapter",
    "AzureAssistantsAdapter",
    "N8NAdapter",
    "VertexAIAdapter",
    # Constraints
    "PLATFORM_CONSTRAINTS",
    "STARTER_TEMPLATES",
    "get_starters_for_department",
    # Unified interface
    "get_adapter",
    "generate_for_platform",
    "generate_for_all_platforms",
    "get_available_platforms",
    "get_platform_constraints",
    "compare_platforms",
]

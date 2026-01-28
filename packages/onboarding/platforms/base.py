"""Base classes for platform adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PlatformType(str, Enum):
    """Supported AI platforms."""
    CHATGPT = "chatgpt"
    COPILOT_STUDIO = "copilot_studio"
    AZURE_ASSISTANTS = "azure_assistants"
    VERTEX_AI = "vertex_ai"
    N8N = "n8n"


@dataclass
class PlatformConfig:
    """Configuration for a specific platform deployment."""
    platform: PlatformType

    # Common settings
    environment: str = "production"

    # Microsoft Copilot Studio specific
    copilot_solution: str | None = None
    copilot_sharepoint_site: str | None = None
    copilot_teams_channel: str | None = None
    copilot_dlp_policy: str | None = None

    # Azure specific
    azure_subscription_id: str | None = None
    azure_resource_group: str | None = None
    azure_openai_endpoint: str | None = None
    azure_deployment_name: str | None = None

    # ChatGPT specific
    chatgpt_visibility: str = "private"  # private, anyone_with_link, public
    chatgpt_enable_web_browsing: bool = False
    chatgpt_enable_code_interpreter: bool = True
    chatgpt_enable_dalle: bool = False

    # N8N specific
    n8n_instance_url: str | None = None
    n8n_webhook_base: str | None = None
    n8n_vector_store: str = "in_memory"  # pinecone, qdrant, supabase, postgres

    # Google Vertex specific
    vertex_project_id: str | None = None
    vertex_location: str = "us-central1"
    vertex_model: str = "gemini-pro"


@dataclass
class AgentOutput:
    """Platform-specific agent output."""
    platform: PlatformType
    agent_id: str
    agent_name: str

    # The generated configuration for the platform
    config: dict[str, Any] = field(default_factory=dict)

    # Files to upload/create
    files: list[dict[str, Any]] = field(default_factory=list)

    # Instructions/notes for manual steps
    manual_steps: list[str] = field(default_factory=list)

    # Validation warnings
    warnings: list[str] = field(default_factory=list)

    # API calls needed to deploy (if supported)
    api_calls: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "platform": self.platform.value,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "config": self.config,
            "files": self.files,
            "manual_steps": self.manual_steps,
            "warnings": self.warnings,
            "api_calls": self.api_calls,
        }


class PlatformAdapter(ABC):
    """Base class for platform adapters."""

    platform: PlatformType

    @abstractmethod
    def adapt(
        self,
        manifest: Any,  # AgentManifest from manifest.py
        platform_config: PlatformConfig,
    ) -> AgentOutput:
        """Convert an agent manifest to platform-specific format.

        Args:
            manifest: The platform-agnostic agent manifest
            platform_config: Platform-specific configuration

        Returns:
            AgentOutput with platform-specific configuration
        """
        pass

    @abstractmethod
    def get_constraints(self) -> dict[str, Any]:
        """Get the constraints for this platform."""
        pass

    def truncate(self, text: str, max_chars: int) -> str:
        """Truncate text to max chars, preserving word boundaries."""
        if len(text) <= max_chars:
            return text

        truncated = text[:max_chars - 3]
        # Find last space to avoid cutting mid-word
        last_space = truncated.rfind(" ")
        if last_space > max_chars * 0.8:
            truncated = truncated[:last_space]

        return truncated + "..."

    def compress_instructions(
        self,
        instructions: str,
        max_chars: int,
        priority_sections: list[str] | None = None,
    ) -> str:
        """Compress instructions to fit platform limits.

        Preserves high-priority sections (identity, safety, governance)
        and compresses or removes lower-priority content.
        """
        if len(instructions) <= max_chars:
            return instructions

        # Default section priorities
        if priority_sections is None:
            priority_sections = [
                "IDENTITY",
                "PROHIBITED ACTIONS",
                "GUARDRAILS",
                "GOVERNANCE",
                "ESCALATION",
                "CAPABILITIES",
                "RESPONSE PROTOCOLS",
            ]

        # Try to preserve complete high-priority sections
        lines = instructions.split("\n")
        result_lines = []
        current_section = None
        section_priority = 999

        for line in lines:
            # Detect section headers
            line_upper = line.upper().strip()
            for i, section in enumerate(priority_sections):
                if section in line_upper:
                    current_section = section
                    section_priority = i
                    break

            # Include lines from high-priority sections
            if section_priority < len(priority_sections) * 0.6:
                result_lines.append(line)

        result = "\n".join(result_lines)

        # If still too long, truncate
        if len(result) > max_chars:
            result = self.truncate(result, max_chars)

        return result

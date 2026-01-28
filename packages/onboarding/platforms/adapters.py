"""Unified platform adapter interface.

Provides a single entry point for generating platform-specific agent configurations.
"""

from __future__ import annotations

from typing import Any

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
from packages.onboarding.platforms.constraints import PLATFORM_CONSTRAINTS


# Registry of all available adapters
_ADAPTERS: dict[PlatformType, type[PlatformAdapter]] = {
    PlatformType.CHATGPT: ChatGPTAdapter,
    PlatformType.COPILOT_STUDIO: CopilotStudioAdapter,
    PlatformType.AZURE_ASSISTANTS: AzureAssistantsAdapter,
    PlatformType.N8N: N8NAdapter,
    PlatformType.VERTEX_AI: VertexAIAdapter,
}


def get_adapter(platform: PlatformType | str) -> PlatformAdapter:
    """Get the adapter for a specific platform.

    Args:
        platform: Platform type enum or string name

    Returns:
        Instantiated platform adapter

    Raises:
        ValueError: If platform is not supported
    """
    if isinstance(platform, str):
        try:
            platform = PlatformType(platform)
        except ValueError:
            # Try mapping common aliases
            aliases = {
                "chatgpt": PlatformType.CHATGPT,
                "gpt": PlatformType.CHATGPT,
                "custom_gpt": PlatformType.CHATGPT,
                "copilot": PlatformType.COPILOT_STUDIO,
                "copilot_studio": PlatformType.COPILOT_STUDIO,
                "microsoft_copilot": PlatformType.COPILOT_STUDIO,
                "azure": PlatformType.AZURE_ASSISTANTS,
                "azure_assistants": PlatformType.AZURE_ASSISTANTS,
                "azure_openai": PlatformType.AZURE_ASSISTANTS,
                "n8n": PlatformType.N8N,
                "vertex": PlatformType.VERTEX_AI,
                "vertex_ai": PlatformType.VERTEX_AI,
                "dialogflow": PlatformType.VERTEX_AI,
                "google": PlatformType.VERTEX_AI,
            }
            platform = aliases.get(platform.lower())
            if platform is None:
                raise ValueError(f"Unknown platform: {platform}")

    adapter_class = _ADAPTERS.get(platform)
    if adapter_class is None:
        raise ValueError(f"No adapter available for platform: {platform}")

    return adapter_class()


def generate_for_platform(
    manifest: Any,
    platform: PlatformType | str,
    platform_config: PlatformConfig | None = None,
) -> AgentOutput:
    """Generate agent configuration for a specific platform.

    Args:
        manifest: Platform-agnostic agent manifest
        platform: Target platform
        platform_config: Optional platform-specific configuration

    Returns:
        Platform-specific agent output
    """
    if isinstance(platform, str):
        platform_type = PlatformType(platform) if platform in [p.value for p in PlatformType] else None
        if platform_type is None:
            # Use get_adapter to resolve aliases
            adapter = get_adapter(platform)
            platform_type = adapter.platform
        platform = platform_type

    # Create default config if not provided
    if platform_config is None:
        platform_config = PlatformConfig(platform=platform)

    adapter = get_adapter(platform)
    return adapter.adapt(manifest, platform_config)


def generate_for_all_platforms(
    manifest: Any,
    platforms: list[PlatformType | str] | None = None,
    platform_configs: dict[str, PlatformConfig] | None = None,
) -> dict[str, AgentOutput]:
    """Generate agent configurations for multiple platforms.

    Args:
        manifest: Platform-agnostic agent manifest
        platforms: List of target platforms (default: all platforms)
        platform_configs: Dict mapping platform names to configs

    Returns:
        Dict mapping platform names to agent outputs
    """
    if platforms is None:
        platforms = list(PlatformType)

    if platform_configs is None:
        platform_configs = {}

    results = {}
    for platform in platforms:
        platform_name = platform.value if isinstance(platform, PlatformType) else platform
        config = platform_configs.get(platform_name)

        try:
            output = generate_for_platform(manifest, platform, config)
            results[platform_name] = output
        except Exception as e:
            # Include error information but don't fail entire batch
            results[platform_name] = AgentOutput(
                platform=platform if isinstance(platform, PlatformType) else PlatformType(platform),
                agent_id=manifest.id,
                agent_name=manifest.name,
                warnings=[f"Generation failed: {str(e)}"],
            )

    return results


def get_available_platforms() -> list[dict[str, Any]]:
    """Get information about all available platforms.

    Returns:
        List of platform information dicts
    """
    platforms = []
    for platform_type in PlatformType:
        constraints = PLATFORM_CONSTRAINTS.get(platform_type.value, {})
        platforms.append({
            "id": platform_type.value,
            "name": constraints.get("display_name", platform_type.value),
            "vendor": constraints.get("vendor", "Unknown"),
            "best_for": constraints.get("best_for", ""),
            "requires": constraints.get("requires", ""),
            "api_deployment": constraints.get("api_deployment", False),
            "constraints": {
                "name_max_chars": constraints.get("name", {}).get("max_chars"),
                "description_max_chars": constraints.get("description", {}).get("max_chars"),
                "instructions_max_chars": constraints.get("instructions", {}).get("max_chars"),
            },
        })
    return platforms


def get_platform_constraints(platform: PlatformType | str) -> dict[str, Any]:
    """Get the constraints for a specific platform.

    Args:
        platform: Platform type or string name

    Returns:
        Platform constraints dict
    """
    if isinstance(platform, PlatformType):
        platform = platform.value

    # Normalize platform name
    platform_map = {
        "chatgpt": "chatgpt",
        "copilot_studio": "copilot_studio",
        "copilot": "copilot_studio",
        "azure_assistants": "azure_assistants",
        "azure": "azure_assistants",
        "n8n": "n8n",
        "vertex_ai": "vertex_ai",
        "vertex": "vertex_ai",
    }
    normalized = platform_map.get(platform.lower(), platform)

    return PLATFORM_CONSTRAINTS.get(normalized, {})


def compare_platforms(
    manifest: Any,
    platforms: list[PlatformType | str] | None = None,
) -> dict[str, Any]:
    """Compare how a manifest would be adapted across platforms.

    Useful for showing users what capabilities each platform supports
    and what content might be truncated.

    Args:
        manifest: Platform-agnostic agent manifest
        platforms: Platforms to compare (default: all)

    Returns:
        Comparison report
    """
    if platforms is None:
        platforms = list(PlatformType)

    comparison = {
        "manifest_id": manifest.id,
        "manifest_name": manifest.name,
        "original_lengths": {
            "name": len(manifest.name),
            "description": len(manifest.description) if manifest.description else 0,
            "system_prompt": len(manifest.system_prompt) if hasattr(manifest, "system_prompt") else 0,
        },
        "platforms": {},
    }

    for platform in platforms:
        platform_name = platform.value if isinstance(platform, PlatformType) else platform
        constraints = get_platform_constraints(platform)

        platform_info = {
            "display_name": constraints.get("display_name", platform_name),
            "fits_without_truncation": True,
            "truncation_warnings": [],
            "capabilities": {},
        }

        # Helper to parse max value (handles "unlimited" string)
        def parse_max(value: Any) -> float:
            if isinstance(value, (int, float)):
                return float(value)
            if value == "unlimited":
                return float("inf")
            return float("inf")

        # Check name
        name_max = parse_max(constraints.get("name", {}).get("max_chars", float("inf")))
        if comparison["original_lengths"]["name"] > name_max:
            platform_info["fits_without_truncation"] = False
            platform_info["truncation_warnings"].append(
                f"Name exceeds {int(name_max)} char limit"
            )

        # Check description
        desc_max = parse_max(constraints.get("description", {}).get("max_chars", float("inf")))
        if comparison["original_lengths"]["description"] > desc_max:
            platform_info["fits_without_truncation"] = False
            platform_info["truncation_warnings"].append(
                f"Description exceeds {int(desc_max)} char limit"
            )

        # Check instructions
        inst_max = parse_max(constraints.get("instructions", {}).get("max_chars", float("inf")))
        if comparison["original_lengths"]["system_prompt"] > inst_max:
            platform_info["fits_without_truncation"] = False
            platform_info["truncation_warnings"].append(
                f"Instructions exceed {int(inst_max)} char limit (has {comparison['original_lengths']['system_prompt']})"
            )

        # Capabilities
        caps = constraints.get("capabilities", {})
        platform_info["capabilities"] = {
            k: v.get("supported", False) if isinstance(v, dict) else v
            for k, v in caps.items()
        }

        comparison["platforms"][platform_name] = platform_info

    # Recommendation
    best_fit = None
    for platform_name, info in comparison["platforms"].items():
        if info["fits_without_truncation"]:
            best_fit = platform_name
            break

    comparison["recommendation"] = {
        "best_fit": best_fit,
        "reason": "Full content without truncation" if best_fit else "All platforms require some truncation",
    }

    return comparison


# Convenience exports
__all__ = [
    "get_adapter",
    "generate_for_platform",
    "generate_for_all_platforms",
    "get_available_platforms",
    "get_platform_constraints",
    "compare_platforms",
    "PlatformAdapter",
    "PlatformConfig",
    "PlatformType",
    "AgentOutput",
]

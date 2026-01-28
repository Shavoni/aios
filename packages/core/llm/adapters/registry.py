"""Model registry for managing LLM adapters."""

from __future__ import annotations

import os
from typing import Any

from packages.core.llm.adapters.base import ModelAdapter
from packages.core.llm.types import ModelTier


# Default models per tier
DEFAULT_TIER_MODELS: dict[ModelTier, list[str]] = {
    ModelTier.REASONING: [
        "openai/o3",
        "openai/o1",
        "anthropic/claude-opus-4-5",
    ],
    ModelTier.GENERATION: [
        "openai/gpt-4o",
        "anthropic/claude-sonnet-4-5",
        "google/gemini-2-pro",
    ],
    ModelTier.CONVERSATION: [
        "openai/gpt-4o-mini",
        "anthropic/claude-haiku",
        "google/gemini-flash",
    ],
    ModelTier.CLASSIFICATION: [
        "openai/gpt-4o-mini",
        "local/llama-3-8b",
    ],
    ModelTier.LOCAL: [
        "local/llama-3-70b",
        "local/llama-3-8b",
        "local/mistral-7b",
    ],
}


class ModelRegistry:
    """Registry for model adapters.

    Manages model configurations and provides adapter instances.
    Supports per-organization model preferences.
    """

    _instance: ModelRegistry | None = None

    def __init__(self):
        self._adapters: dict[str, ModelAdapter] = {}
        self._org_preferences: dict[str, dict[ModelTier, list[str]]] = {}
        self._available_models: set[str] = set()
        self._initialize_defaults()

    @classmethod
    def get_instance(cls) -> ModelRegistry:
        """Get singleton registry instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (for testing)."""
        cls._instance = None

    def _initialize_defaults(self) -> None:
        """Initialize with default available models based on environment."""
        # Check which API keys are available
        if os.environ.get("OPENAI_API_KEY"):
            self._available_models.update([
                "openai/gpt-4o",
                "openai/gpt-4o-mini",
                "openai/gpt-4-turbo",
                "openai/o1",
                "openai/o3",
            ])

        if os.environ.get("ANTHROPIC_API_KEY"):
            self._available_models.update([
                "anthropic/claude-opus-4-5",
                "anthropic/claude-sonnet-4-5",
                "anthropic/claude-haiku",
            ])

        # Local models are always "available" but may not be running
        self._available_models.update([
            "local/llama-3-70b",
            "local/llama-3-8b",
            "local/mistral-7b",
        ])

    def get_adapter(self, model_id: str) -> ModelAdapter:
        """Get or create an adapter for the specified model.

        Args:
            model_id: Full model ID (e.g., "openai/gpt-4o")

        Returns:
            ModelAdapter instance

        Raises:
            ValueError: If model provider is unknown
        """
        if model_id in self._adapters:
            return self._adapters[model_id]

        adapter = self._create_adapter(model_id)
        self._adapters[model_id] = adapter
        return adapter

    def _create_adapter(self, model_id: str) -> ModelAdapter:
        """Create a new adapter for the model."""
        if "/" not in model_id:
            raise ValueError(f"Invalid model ID format: {model_id}. Expected 'provider/model'")

        provider, model = model_id.split("/", 1)

        if provider == "openai":
            from packages.core.llm.adapters.openai_adapter import OpenAIAdapter
            return OpenAIAdapter(model=model)

        elif provider == "anthropic":
            from packages.core.llm.adapters.anthropic_adapter import AnthropicAdapter
            return AnthropicAdapter(model=model)

        elif provider == "local":
            from packages.core.llm.adapters.local_adapter import LocalModelAdapter
            return LocalModelAdapter(model=model)

        else:
            raise ValueError(f"Unknown model provider: {provider}")

    def register_adapter(self, model_id: str, adapter: ModelAdapter) -> None:
        """Register a custom adapter.

        Args:
            model_id: Full model ID
            adapter: Adapter instance
        """
        self._adapters[model_id] = adapter
        self._available_models.add(model_id)

    def is_available(self, model_id: str) -> bool:
        """Check if a model is available."""
        return model_id in self._available_models

    def get_available_models(self, tier: ModelTier | None = None) -> list[str]:
        """Get list of available models, optionally filtered by tier.

        Args:
            tier: Optional tier to filter by

        Returns:
            List of available model IDs
        """
        if tier is None:
            return list(self._available_models)

        tier_models = DEFAULT_TIER_MODELS.get(tier, [])
        return [m for m in tier_models if m in self._available_models]

    def get_tier_models(
        self,
        tier: ModelTier,
        org_id: str | None = None,
    ) -> list[str]:
        """Get models for a tier, respecting org preferences.

        Args:
            tier: Model tier
            org_id: Optional organization ID for preferences

        Returns:
            List of model IDs in preference order
        """
        # Check org-specific preferences
        if org_id and org_id in self._org_preferences:
            org_prefs = self._org_preferences[org_id]
            if tier in org_prefs:
                return [m for m in org_prefs[tier] if self.is_available(m)]

        # Fall back to defaults
        return self.get_available_models(tier)

    def set_org_preferences(
        self,
        org_id: str,
        preferences: dict[ModelTier, list[str]],
    ) -> None:
        """Set model preferences for an organization.

        Args:
            org_id: Organization ID
            preferences: Dict mapping tiers to model lists
        """
        self._org_preferences[org_id] = preferences

    def get_primary_model(
        self,
        tier: ModelTier,
        org_id: str | None = None,
    ) -> str | None:
        """Get the primary (first available) model for a tier.

        Args:
            tier: Model tier
            org_id: Optional organization ID

        Returns:
            Model ID or None if none available
        """
        models = self.get_tier_models(tier, org_id)
        return models[0] if models else None

    def get_fallback_model(
        self,
        tier: ModelTier,
        org_id: str | None = None,
    ) -> str | None:
        """Get the fallback model for a tier.

        Args:
            tier: Model tier
            org_id: Optional organization ID

        Returns:
            Model ID or None if none available
        """
        models = self.get_tier_models(tier, org_id)
        return models[1] if len(models) > 1 else (models[0] if models else None)

    async def check_model_health(self, model_id: str) -> dict[str, Any]:
        """Check health of a specific model.

        Args:
            model_id: Model to check

        Returns:
            Health status dict
        """
        try:
            adapter = self.get_adapter(model_id)
            return await adapter.health_check()
        except Exception as e:
            return {"healthy": False, "error": str(e)}

    async def get_all_health(self) -> dict[str, dict[str, Any]]:
        """Check health of all available models.

        Returns:
            Dict mapping model IDs to health status
        """
        results = {}
        for model_id in self._available_models:
            results[model_id] = await self.check_model_health(model_id)
        return results


def get_model_registry() -> ModelRegistry:
    """Get the singleton model registry."""
    return ModelRegistry.get_instance()


def get_adapter(model_id: str) -> ModelAdapter:
    """Get an adapter for the specified model.

    Convenience function that uses the singleton registry.
    """
    return get_model_registry().get_adapter(model_id)


def register_adapter(model_id: str, adapter: ModelAdapter) -> None:
    """Register a custom adapter.

    Convenience function that uses the singleton registry.
    """
    get_model_registry().register_adapter(model_id, adapter)

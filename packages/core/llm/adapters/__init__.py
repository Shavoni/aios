"""Model adapters for different LLM providers."""

from packages.core.llm.adapters.base import ModelAdapter
from packages.core.llm.adapters.openai_adapter import OpenAIAdapter
from packages.core.llm.adapters.anthropic_adapter import AnthropicAdapter
from packages.core.llm.adapters.local_adapter import LocalModelAdapter
from packages.core.llm.adapters.registry import (
    ModelRegistry,
    get_adapter,
    register_adapter,
    get_model_registry,
)

__all__ = [
    "ModelAdapter",
    "OpenAIAdapter",
    "AnthropicAdapter",
    "LocalModelAdapter",
    "ModelRegistry",
    "get_adapter",
    "register_adapter",
    "get_model_registry",
]

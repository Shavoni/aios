"""Base model adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from packages.core.llm.types import ModelResponse
    from packages.core.llm.prompts.base import PromptTemplate


class ModelAdapter(ABC):
    """Base class for model-specific adapters.

    Adapters translate aiOS prompts and handle model-specific quirks.
    Each adapter knows how to optimize prompts for its model and
    how to parse responses into the expected format.
    """

    provider: str = "base"
    model: str = ""
    supports_json_mode: bool = False
    supports_streaming: bool = True
    supports_function_calling: bool = False
    max_context_length: int = 8192
    is_reasoning_model: bool = False

    def __init__(self, model: str, **kwargs: Any):
        """Initialize the adapter with model ID and optional config."""
        self.model = model
        self._config = kwargs

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        max_tokens: int = 4000,
        temperature: float = 0.7,
        system_prompt: str | None = None,
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> "ModelResponse":
        """Execute a completion request.

        Args:
            prompt: The user prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            system_prompt: Optional system prompt
            response_format: Optional format specification (e.g., {"type": "json_object"})
            **kwargs: Additional model-specific parameters

        Returns:
            ModelResponse with content and metadata
        """
        pass

    def optimize_prompt(
        self,
        prompt: str,
        template: "PromptTemplate | None" = None,
    ) -> str:
        """Optimize a prompt for this specific model.

        Override in subclasses to add model-specific optimizations.

        Args:
            prompt: The base prompt
            template: Optional template with output format requirements

        Returns:
            Optimized prompt string
        """
        return prompt

    def parse_response(
        self,
        response: str,
        expected_format: str = "text",
    ) -> dict[str, Any] | str:
        """Parse model response into expected format.

        Args:
            response: Raw response text
            expected_format: Expected format (text, json, markdown)

        Returns:
            Parsed response
        """
        if expected_format == "json":
            import json
            # Try to extract JSON from response
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                # Try to find JSON in the response
                import re
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    try:
                        return json.loads(json_match.group())
                    except json.JSONDecodeError:
                        pass
                return {"raw": response, "parse_error": True}
        return response

    def get_model_id(self) -> str:
        """Get the full model identifier."""
        return f"{self.provider}/{self.model}"

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.

        This is a rough estimate. Override for model-specific tokenization.
        """
        # Rough estimate: ~4 characters per token
        return len(text) // 4

    async def health_check(self) -> dict[str, Any]:
        """Check if the model is available and responsive.

        Returns:
            Dict with 'healthy' bool and optional 'latency_ms'
        """
        try:
            import time
            start = time.time()
            await self.complete(
                prompt="Say 'ok'",
                max_tokens=10,
                temperature=0,
            )
            latency = (time.time() - start) * 1000
            return {"healthy": True, "latency_ms": latency}
        except Exception as e:
            return {"healthy": False, "error": str(e)}

"""OpenAI model adapter."""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING, Any

from packages.core.llm.adapters.base import ModelAdapter
from packages.core.llm.types import ModelResponse

if TYPE_CHECKING:
    from packages.core.llm.prompts.base import PromptTemplate


class OpenAIAdapter(ModelAdapter):
    """Adapter for OpenAI models (GPT-4o, o1, o3, etc.)."""

    provider = "openai"
    supports_json_mode = True
    supports_streaming = True
    supports_function_calling = True

    # Model-specific configurations
    MODEL_CONFIGS = {
        "o3": {"max_context": 200000, "is_reasoning": True},
        "o1": {"max_context": 200000, "is_reasoning": True},
        "o1-mini": {"max_context": 128000, "is_reasoning": True},
        "gpt-4o": {"max_context": 128000, "is_reasoning": False},
        "gpt-4o-mini": {"max_context": 128000, "is_reasoning": False},
        "gpt-4-turbo": {"max_context": 128000, "is_reasoning": False},
        "gpt-4": {"max_context": 8192, "is_reasoning": False},
        "gpt-3.5-turbo": {"max_context": 16384, "is_reasoning": False},
    }

    def __init__(self, model: str = "gpt-4o", api_key: str | None = None, **kwargs: Any):
        """Initialize OpenAI adapter.

        Args:
            model: Model name (e.g., "gpt-4o", "o3")
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            **kwargs: Additional configuration
        """
        super().__init__(model, **kwargs)

        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self._api_key:
            raise ValueError("OpenAI API key required")

        # Set model-specific config
        config = self.MODEL_CONFIGS.get(model, {"max_context": 8192, "is_reasoning": False})
        self.max_context_length = config["max_context"]
        self.is_reasoning_model = config["is_reasoning"]

        # Initialize client lazily
        self._client = None

    @property
    def client(self):
        """Get or create the OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=self._api_key)
            except ImportError:
                raise ImportError("openai package required. Install with: pip install openai")
        return self._client

    def optimize_prompt(
        self,
        prompt: str,
        template: "PromptTemplate | None" = None,
    ) -> str:
        """Optimize prompt for OpenAI models."""
        if self.is_reasoning_model:
            # o1/o3 models work better with clear problem statements
            # and don't need explicit "think step by step" instructions
            return f"""Problem to solve:

{prompt}

Provide your analysis and final answer."""
        return prompt

    async def complete(
        self,
        prompt: str,
        max_tokens: int = 4000,
        temperature: float = 0.7,
        system_prompt: str | None = None,
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> ModelResponse:
        """Execute completion with OpenAI model."""
        start_time = time.time()

        messages = []
        if system_prompt and not self.is_reasoning_model:
            # Reasoning models don't support system prompts
            messages.append({"role": "system", "content": system_prompt})
        elif system_prompt and self.is_reasoning_model:
            # Prepend system content to user prompt for reasoning models
            prompt = f"{system_prompt}\n\n{prompt}"

        messages.append({"role": "user", "content": prompt})

        params: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_completion_tokens" if self.is_reasoning_model else "max_tokens": max_tokens,
        }

        # Reasoning models don't support temperature
        if not self.is_reasoning_model:
            params["temperature"] = temperature

        # JSON mode
        if response_format and self.supports_json_mode:
            params["response_format"] = response_format

        try:
            response = await self.client.chat.completions.create(**params)

            latency = (time.time() - start_time) * 1000

            return ModelResponse(
                content=response.choices[0].message.content or "",
                model=self.model,
                provider=self.provider,
                prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                completion_tokens=response.usage.completion_tokens if response.usage else 0,
                total_tokens=response.usage.total_tokens if response.usage else 0,
                latency_ms=latency,
                finish_reason=response.choices[0].finish_reason or "stop",
                request_id=response.id,
            )

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            raise RuntimeError(f"OpenAI API error after {latency:.0f}ms: {e}") from e

    def parse_response(
        self,
        response: str,
        expected_format: str = "text",
    ) -> dict[str, Any] | str:
        """Parse OpenAI response."""
        if expected_format == "json":
            import json
            try:
                # OpenAI with JSON mode usually returns clean JSON
                return json.loads(response)
            except json.JSONDecodeError:
                # Fall back to base parsing
                return super().parse_response(response, expected_format)
        return response

    def estimate_tokens(self, text: str) -> int:
        """Estimate tokens using tiktoken if available."""
        try:
            import tiktoken
            encoding = tiktoken.encoding_for_model(self.model)
            return len(encoding.encode(text))
        except (ImportError, KeyError):
            # Fall back to rough estimate
            return super().estimate_tokens(text)

"""Anthropic Claude model adapter."""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING, Any

from packages.core.llm.adapters.base import ModelAdapter
from packages.core.llm.types import ModelResponse

if TYPE_CHECKING:
    from packages.core.llm.prompts.base import PromptTemplate


class AnthropicAdapter(ModelAdapter):
    """Adapter for Anthropic Claude models."""

    provider = "anthropic"
    supports_json_mode = False  # Claude uses prompt-based JSON
    supports_streaming = True
    supports_function_calling = True

    # Model-specific configurations
    MODEL_CONFIGS = {
        "claude-opus-4-5": {"max_context": 200000, "max_output": 32000},
        "claude-sonnet-4-5": {"max_context": 200000, "max_output": 16000},
        "claude-3-opus": {"max_context": 200000, "max_output": 4096},
        "claude-3-sonnet": {"max_context": 200000, "max_output": 4096},
        "claude-3-haiku": {"max_context": 200000, "max_output": 4096},
        "claude-haiku": {"max_context": 200000, "max_output": 8192},
    }

    def __init__(self, model: str = "claude-sonnet-4-5", api_key: str | None = None, **kwargs: Any):
        """Initialize Anthropic adapter.

        Args:
            model: Model name (e.g., "claude-opus-4-5", "claude-sonnet-4-5")
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            **kwargs: Additional configuration
        """
        super().__init__(model, **kwargs)

        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self._api_key:
            raise ValueError("Anthropic API key required")

        # Set model-specific config
        config = self.MODEL_CONFIGS.get(model, {"max_context": 200000, "max_output": 4096})
        self.max_context_length = config["max_context"]
        self._max_output = config["max_output"]

        # Initialize client lazily
        self._client = None

    @property
    def client(self):
        """Get or create the Anthropic client."""
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic
                self._client = AsyncAnthropic(api_key=self._api_key)
            except ImportError:
                raise ImportError("anthropic package required. Install with: pip install anthropic")
        return self._client

    def optimize_prompt(
        self,
        prompt: str,
        template: "PromptTemplate | None" = None,
    ) -> str:
        """Optimize prompt for Claude models."""
        # Claude responds well to clear structure and explicit format instructions
        if template and template.output_format == "json":
            return f"""{prompt}

Respond with valid JSON only. Do not include any text before or after the JSON object.
Do not include markdown code blocks around the JSON."""
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
        """Execute completion with Claude model."""
        start_time = time.time()

        # Respect model's max output limit
        max_tokens = min(max_tokens, self._max_output)

        messages = [{"role": "user", "content": prompt}]

        params: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }

        if system_prompt:
            params["system"] = system_prompt

        try:
            response = await self.client.messages.create(**params)

            latency = (time.time() - start_time) * 1000

            # Extract content from response
            content = ""
            if response.content:
                content = response.content[0].text if response.content else ""

            return ModelResponse(
                content=content,
                model=self.model,
                provider=self.provider,
                prompt_tokens=response.usage.input_tokens if response.usage else 0,
                completion_tokens=response.usage.output_tokens if response.usage else 0,
                total_tokens=(
                    (response.usage.input_tokens + response.usage.output_tokens)
                    if response.usage else 0
                ),
                latency_ms=latency,
                finish_reason=response.stop_reason or "end_turn",
                request_id=response.id,
            )

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            raise RuntimeError(f"Anthropic API error after {latency:.0f}ms: {e}") from e

    def parse_response(
        self,
        response: str,
        expected_format: str = "text",
    ) -> dict[str, Any] | str:
        """Parse Claude response."""
        if expected_format == "json":
            import json
            import re

            # Claude sometimes wraps JSON in markdown code blocks
            # Remove them if present
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                # Try to find JSON object in response
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    try:
                        return json.loads(json_match.group())
                    except json.JSONDecodeError:
                        pass
                return {"raw": response, "parse_error": True}
        return response

    def estimate_tokens(self, text: str) -> int:
        """Estimate tokens for Claude.

        Claude uses a similar tokenization to GPT models.
        """
        # Roughly 4 characters per token, slightly more conservative
        return int(len(text) / 3.5)

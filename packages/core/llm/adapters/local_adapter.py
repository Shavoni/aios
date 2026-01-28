"""Local model adapter for Ollama, vLLM, LMStudio, etc."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from packages.core.llm.adapters.base import ModelAdapter
from packages.core.llm.types import ModelResponse

if TYPE_CHECKING:
    from packages.core.llm.prompts.base import PromptTemplate


class LocalModelAdapter(ModelAdapter):
    """Adapter for local models via Ollama, vLLM, or compatible APIs."""

    provider = "local"
    supports_json_mode = False
    supports_streaming = True
    supports_function_calling = False

    # Common local model configurations
    MODEL_CONFIGS = {
        "llama-3-70b": {"max_context": 8192},
        "llama-3-8b": {"max_context": 8192},
        "llama-3.1-70b": {"max_context": 128000},
        "llama-3.1-8b": {"max_context": 128000},
        "mistral-7b": {"max_context": 32768},
        "mixtral-8x7b": {"max_context": 32768},
        "phi-3": {"max_context": 4096},
        "qwen-2-72b": {"max_context": 32768},
        "deepseek-coder": {"max_context": 16384},
    }

    def __init__(
        self,
        model: str = "llama-3-8b",
        endpoint: str = "http://localhost:11434",
        api_type: str = "ollama",
        **kwargs: Any,
    ):
        """Initialize local model adapter.

        Args:
            model: Model name (e.g., "llama-3-8b", "mistral-7b")
            endpoint: API endpoint URL
            api_type: API type ("ollama", "vllm", "openai-compatible")
            **kwargs: Additional configuration
        """
        super().__init__(model, **kwargs)

        self._endpoint = endpoint.rstrip("/")
        self._api_type = api_type

        # Set model-specific config
        config = self.MODEL_CONFIGS.get(model, {"max_context": 4096})
        self.max_context_length = config["max_context"]

    def optimize_prompt(
        self,
        prompt: str,
        template: "PromptTemplate | None" = None,
    ) -> str:
        """Optimize prompt for local models.

        Local models often need more explicit instructions.
        """
        if template and template.output_format == "json":
            return f"""IMPORTANT: You must respond with valid JSON only. No additional text or explanation.

{prompt}

Remember: Output ONLY valid JSON, nothing else."""
        return prompt

    async def complete(
        self,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        system_prompt: str | None = None,
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> ModelResponse:
        """Execute completion with local model."""
        start_time = time.time()

        if self._api_type == "ollama":
            return await self._complete_ollama(
                prompt, max_tokens, temperature, system_prompt, start_time
            )
        elif self._api_type == "openai-compatible":
            return await self._complete_openai_compatible(
                prompt, max_tokens, temperature, system_prompt, start_time
            )
        else:
            # Default to Ollama
            return await self._complete_ollama(
                prompt, max_tokens, temperature, system_prompt, start_time
            )

    async def _complete_ollama(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        system_prompt: str | None,
        start_time: float,
    ) -> ModelResponse:
        """Complete using Ollama API."""
        try:
            import aiohttp
        except ImportError:
            raise ImportError("aiohttp required for local models. Install with: pip install aiohttp")

        # Build full prompt with system
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
            "stream": False,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self._endpoint}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=300),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise RuntimeError(f"Ollama error {response.status}: {error_text}")

                    result = await response.json()

            latency = (time.time() - start_time) * 1000

            return ModelResponse(
                content=result.get("response", ""),
                model=self.model,
                provider=self.provider,
                prompt_tokens=result.get("prompt_eval_count", 0),
                completion_tokens=result.get("eval_count", 0),
                total_tokens=result.get("prompt_eval_count", 0) + result.get("eval_count", 0),
                latency_ms=latency,
                finish_reason="stop" if result.get("done") else "length",
            )

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            raise RuntimeError(f"Local model error after {latency:.0f}ms: {e}") from e

    async def _complete_openai_compatible(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        system_prompt: str | None,
        start_time: float,
    ) -> ModelResponse:
        """Complete using OpenAI-compatible API (vLLM, LMStudio, etc.)."""
        try:
            import aiohttp
        except ImportError:
            raise ImportError("aiohttp required for local models. Install with: pip install aiohttp")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self._endpoint}/v1/chat/completions",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=300),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise RuntimeError(f"API error {response.status}: {error_text}")

                    result = await response.json()

            latency = (time.time() - start_time) * 1000

            choice = result.get("choices", [{}])[0]
            usage = result.get("usage", {})

            return ModelResponse(
                content=choice.get("message", {}).get("content", ""),
                model=self.model,
                provider=self.provider,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
                latency_ms=latency,
                finish_reason=choice.get("finish_reason", "stop"),
            )

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            raise RuntimeError(f"Local model error after {latency:.0f}ms: {e}") from e

    async def health_check(self) -> dict[str, Any]:
        """Check if local model is available."""
        try:
            import aiohttp
        except ImportError:
            return {"healthy": False, "error": "aiohttp not installed"}

        try:
            start = time.time()

            if self._api_type == "ollama":
                endpoint = f"{self._endpoint}/api/tags"
            else:
                endpoint = f"{self._endpoint}/v1/models"

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    endpoint,
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response:
                    if response.status == 200:
                        latency = (time.time() - start) * 1000
                        return {"healthy": True, "latency_ms": latency}
                    else:
                        return {"healthy": False, "error": f"Status {response.status}"}

        except Exception as e:
            return {"healthy": False, "error": str(e)}
